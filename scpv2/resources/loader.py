"""
scpv2.resources.loader — JSON 서비스 정의를 Session에 등록 (botocore.loaders.Loader와 동일)
"""
import json
import os
import re

from ..collection import CollectionManager
from ..exceptions import ValidationError
from ..session    import Session


# ── 파라미터 유효성 검사 ─────────────────────────────────────────────────────

def _validate(params: dict, required: list, validations: dict):
    """파라미터 유효성 검사

    1단계: required — 필수 항목 존재 여부
    2단계: validation — regex / enum 형식 검사 (optional은 값이 없으면 건너뜀)
    """
    for param_name in required:
        value = params.get(param_name)
        if value is None or value == "":
            raise ValidationError(f"[{param_name}] 필수 항목입니다")

    for param_name, rule in validations.items():
        value = params.get(param_name)
        if value is None:
            continue

        if rule["type"] == "regex":
            if not re.match(rule["pattern"], str(value)):
                raise ValidationError(
                    f"[{param_name}] {rule['message']} / 입력값: '{value}'"
                )
        elif rule["type"] == "enum":
            if value not in rule["values"]:
                raise ValidationError(
                    f"[{param_name}] {rule['message']}\n"
                    f"  허용값: {rule['values']}\n"
                    f"  입력값: '{value}'"
                )


# ── Mock 응답 빌더 ───────────────────────────────────────────────────────────

def _build_response(template, params: dict):
    """JSON 응답 템플릿에 파라미터를 치환하여 mock 응답 생성"""
    if isinstance(template, str):
        for name, value in params.items():
            template = template.replace(f"${name}", str(value))
        return template
    elif isinstance(template, dict):
        return {k: _build_response(v, params) for k, v in template.items()}
    elif isinstance(template, list):
        return [_build_response(item, params) for item in template]
    return template


# ── 동적 메서드 팩토리 ────────────────────────────────────────────────────────

def _make_client_method(
    method_name:      str,
    param_names:      list,
    required:         list,
    validations:      dict,
    response_template: dict = None,
    http_method:      str   = None,
    path:             str   = None,
    api_name:         str   = None,
    version:          str   = None,
    body_param_names: list  = None,
):
    """JSON 정의로부터 Client 메서드를 동적 생성

    - response_template 있으면 → mock 모드 (로컬 응답 반환)
    - http_method + path 있으면 → real 모드 (SCP API 호출)
    """
    body_param_set = set(body_param_names or [])

    def method(self, *args, **kwargs):
        # 위치 인수 → dict
        params = {}
        for i, name in enumerate(param_names):
            if i < len(args):
                params[name] = args[i]
            elif name in kwargs:
                params[name] = kwargs[name]

        if required or validations:
            _validate(params, required, validations)

        # real HTTP 모드
        if http_method and path:
            resolved_path = path
            for name, value in params.items():
                resolved_path = resolved_path.replace(f"{{{name}}}", str(value))
            path_vars = {k for k in params if f"{{{k}}}" in path}

            if body_param_set:
                query_params = {k: v for k, v in params.items()
                                if k not in body_param_set and k not in path_vars}
                body = {k: v for k, v in params.items() if k in body_param_set}
            else:
                query_params = {k: v for k, v in params.items() if k not in path_vars}
                body = None

            return self._request(
                http_method=http_method,
                path=resolved_path,
                api_name=api_name,
                version=version,
                query_params=query_params or None,
                body=body or None,
                operation_name=method_name,
            )

        # mock 모드
        return _build_response(response_template, params)

    method.__name__ = method_name
    return method


def _make_resource_method(method_name: str, delegates_to: str):
    """ServiceResource 메서드를 동적 생성 — Client 메서드로 위임"""
    def method(self, *args, **kwargs):
        return getattr(self._client, delegates_to)(*args, **kwargs)
    method.__name__ = method_name
    return method


# ── ServiceLoader ────────────────────────────────────────────────────────────

class ServiceLoader:
    """JSON 서비스 정의 파일을 읽어 Session에 등록 (botocore.loaders.Loader와 동일)"""

    DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

    @classmethod
    def load_all(cls):
        for filename in sorted(os.listdir(cls.DATA_DIR)):
            if filename.endswith(".json"):
                cls.load(os.path.join(cls.DATA_DIR, filename))

    @classmethod
    def load(cls, filepath: str):
        with open(filepath) as f:
            definition = json.load(f)

        service_name    = definition["service_name"]
        service_version = definition.get("version", "1.0")
        api_name        = definition.get("api_name", service_name)

        # ── Client 메서드 ──────────────────────────────────────────────
        client_methods = {
            method_name: _make_client_method(
                method_name       = method_name,
                param_names       = spec["params"],
                required          = spec.get("required", []),
                validations       = spec.get("validation", {}),
                response_template = spec.get("response"),
                http_method       = spec.get("http_method"),
                path              = spec.get("path"),
                api_name          = api_name,
                version           = spec.get("version", service_version),
                body_param_names  = spec.get("body_params"),
            )
            for method_name, spec in definition["client_methods"].items()
        }

        # ── ServiceResource 메서드 ─────────────────────────────────────
        resource_methods = {
            method_name: _make_resource_method(method_name, spec["delegates_to"])
            for method_name, spec in definition["resource_methods"].items()
        }

        # ── CollectionManager 디스크립터 ───────────────────────────────
        collection_managers = {
            coll_name: CollectionManager(
                method_name = coll_spec["method"],
                result_key  = coll_spec["result_key"],
                page_param  = coll_spec.get("page_param", "page"),
                size_param  = coll_spec.get("size_param", "size"),
            )
            for coll_name, coll_spec in definition.get("collections", {}).items()
        }

        # ── Paginator 설정 ─────────────────────────────────────────────
        paginator_configs = definition.get("paginators")

        # ── Waiter 설정 ────────────────────────────────────────────────
        waiter_configs = definition.get("waiters")

        Session.register(
            service_name        = service_name,
            client_methods      = client_methods,
            resource_methods    = resource_methods,
            collection_managers = collection_managers or None,
            paginator_configs   = paginator_configs,
            waiter_configs      = waiter_configs,
        )
