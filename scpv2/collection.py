"""
scpv2.collection — resource의 목록 속성을 자동 페이지네이션으로 순회하는 컬렉션

JSON 서비스 정의 스키마::

    "collections": {
        "vpcs": {
            "method":     "list_vpcs",    # 호출할 Client 메서드
            "result_key": "contents"      # 응답에서 목록을 담는 키
        }
    }

사용 예::

    vpc = sess.resource("vpc")

    # 전체 순회 (자동 페이지네이션)
    for v in vpc.vpcs.all():
        print(v["vpcName"])

    # 필터 적용
    for v in vpc.vpcs.filter(vpcState="ACTIVE"):
        print(v)

    # 처음 N개만
    first_5 = vpc.vpcs.limit(5)
"""
from __future__ import annotations

from typing import Callable, Iterator


class Collection:
    """자동 페이지네이션을 지원하는 리소스 컬렉션 이터레이터

    filter(), all(), page_size(), limit() 호출은 새 Collection을 반환하여
    메서드 체이닝을 지원합니다.
    """

    def __init__(
        self,
        method: Callable,
        result_key: str,
        page_param: str = "page",
        size_param: str = "size",
        filters: dict = None,
        _page_size: int = 20,
    ):
        self._method     = method
        self._result_key = result_key
        self._page_param = page_param
        self._size_param = size_param
        self._filters    = filters or {}
        self._page_size  = _page_size

    # ── 이터레이션 ───────────────────────────────────────────────────────

    def __iter__(self) -> Iterator[dict]:
        page = 0
        while True:
            response = self._method(
                **{self._size_param: self._page_size, self._page_param: page},
                **self._filters,
            )
            items = response.get(self._result_key, [])
            yield from items
            if len(items) < self._page_size:
                break
            page += 1

    # ── 체이닝 메서드 ─────────────────────────────────────────────────────

    def all(self) -> "Collection":
        """필터 없이 전체 컬렉션 반환"""
        return self

    def filter(self, **kwargs) -> "Collection":
        """추가 필터를 적용한 새 컬렉션 반환

        Args:
            **kwargs: API 메서드의 필터 파라미터 (예: vpcState="ACTIVE")
        """
        return Collection(
            self._method,
            self._result_key,
            self._page_param,
            self._size_param,
            {**self._filters, **kwargs},
            self._page_size,
        )

    def page_size(self, size: int) -> "Collection":
        """페이지 크기를 변경한 새 컬렉션 반환"""
        return Collection(
            self._method,
            self._result_key,
            self._page_param,
            self._size_param,
            self._filters,
            size,
        )

    def limit(self, count: int) -> list:
        """처음 count개의 항목만 리스트로 반환"""
        results = []
        for item in self:
            results.append(item)
            if len(results) >= count:
                break
        return results


class CollectionManager:
    """ServiceResource에 컬렉션 속성을 제공하는 디스크립터

    type()으로 동적 생성된 ServiceResource 서브클래스에 주입됩니다.
    속성에 접근하면 Collection 인스턴스를 반환합니다.
    """

    def __init__(
        self,
        method_name: str,
        result_key: str,
        page_param: str = "page",
        size_param: str = "size",
    ):
        self._method_name = method_name
        self._result_key  = result_key
        self._page_param  = page_param
        self._size_param  = size_param

    def __set_name__(self, owner, name: str):
        self._attr_name = name

    def __get__(self, obj, objtype=None) -> "CollectionManager | Collection":
        if obj is None:
            return self
        method = getattr(obj._client, self._method_name)
        return Collection(
            method,
            self._result_key,
            self._page_param,
            self._size_param,
        )
