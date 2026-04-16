"""
scpv2.paginator — 페이지네이터 (boto3.paginate와 동일한 구조)

boto3 대응:
    Paginator    ←→ botocore.paginate.Paginator
    PageIterator ←→ botocore.paginate.PageIterator

JSON 서비스 정의 스키마::

    "paginators": {
        "list_vpcs": {
            "input_token":     "page",          # 페이지 번호 파라미터 이름
            "limit_key":       "size",          # 페이지 크기 파라미터 이름
            "result_key":      "contents",      # 응답에서 목록을 담는 키
            "starting_token":  0,               # 시작 페이지 (기본 0)
            "default_page_size": 20             # 기본 페이지 크기 (기본 20)
        }
    }

사용 예::

    paginator = vpc_client.get_paginator("list_vpcs")

    # 페이지 단위로 순회
    for page in paginator.paginate(size=10):
        for vpc in page["contents"]:
            print(vpc)

    # 전체를 한 번에 수집
    result = paginator.paginate().build_full_result()
    all_vpcs = result["contents"]
"""
from __future__ import annotations

from typing import Callable, Iterator

from .exceptions import PaginationError


class PageIterator:
    """페이지 단위 이터레이터

    각 iteration이 API를 한 번 호출하고 페이지 응답 dict를 반환합니다.
    마지막 페이지는 result_key의 항목 수가 limit_key보다 적을 때 감지합니다.
    """

    def __init__(self, method: Callable, config: dict, **kwargs):
        self._method = method
        self._config = config
        self._kwargs = kwargs

    def __iter__(self) -> Iterator[dict]:
        input_token = self._config.get("input_token", "page")
        limit_key   = self._config.get("limit_key", "size")
        result_key  = self._config.get("result_key")
        start       = self._config.get("starting_token", 0)
        page_size   = self._kwargs.pop(limit_key, self._config.get("default_page_size", 20))

        current = start
        while True:
            params   = {**self._kwargs, input_token: current, limit_key: page_size}
            response = self._method(**params)
            yield response

            items = response.get(result_key, []) if result_key else []
            if len(items) < page_size:
                break
            current += 1

    def build_full_result(self) -> dict:
        """모든 페이지를 순회하여 result_key 항목을 하나의 리스트로 합친 dict 반환

        사용 예::

            result = paginator.paginate().build_full_result()
            all_vpcs = result["contents"]
        """
        result_key = self._config.get("result_key")
        all_items: list = []
        merged: dict = {}

        for page in self:
            if result_key:
                all_items.extend(page.get(result_key, []))
                merged = {k: v for k, v in page.items() if k != result_key and k != "ResponseMetadata"}
            else:
                merged.update(page)

        if result_key:
            merged[result_key] = all_items
        return merged


class Paginator:
    """특정 API 작업에 대한 페이지네이터

    boto3와 동일하게 client.get_paginator(operation_name)으로 획득합니다.
    """

    PAGE_ITERATOR_CLASS = PageIterator

    def __init__(self, method: Callable, config: dict):
        if not config:
            raise PaginationError("Paginator config must not be empty")
        self._method = method
        self._config = config

    def paginate(self, **kwargs) -> PageIterator:
        """페이지 이터레이터를 반환합니다.

        Args:
            **kwargs: 해당 API 메서드의 필터 파라미터.
                      limit_key(예: size)를 넘기면 페이지 크기를 override합니다.

        Returns:
            PageIterator: 페이지 단위로 순회 가능한 이터레이터
        """
        return self.PAGE_ITERATOR_CLASS(self._method, self._config, **kwargs)
