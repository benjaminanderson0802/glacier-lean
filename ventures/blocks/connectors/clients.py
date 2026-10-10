"""Read-only clients for Jobber, ShipStation, Shopify Admin, and Apify."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from .common import ConnectorError, ReadOnlyClient, UnauthorizedError, glacier_secret_writer


JOBBER_GRAPHQL_URL = "https://api.getjobber.com/api/graphql"
JOBBER_API_VERSION = "2026-04-16"
SHIPSTATION_API_URL = "https://api.shipstation.com/v2"
SHOPIFY_API_VERSION = "2026-10"
APIFY_API_URL = "https://api.apify.com/v2"


class JobberClient(ReadOnlyClient):
    def __init__(self, *, access_token: str | None = None, secret_name: str = "jobber_access_token", client_id_secret: str = "jobber_client_id", client_secret_secret: str = "jobber_client_secret", refresh_token_secret: str = "jobber_refresh_token", secret_writer: Any = None, api_version: str = JOBBER_API_VERSION, **kwargs: Any):
        super().__init__(secret_name=secret_name, access_token=access_token, **kwargs)
        self.api_version = api_version
        self.client_id_secret = client_id_secret
        self.client_secret_secret = client_secret_secret
        self.refresh_token_secret = refresh_token_secret
        self._secret_writer = secret_writer

    def _write_secret(self, name: str, value: str) -> None:
        writer = self._secret_writer
        if writer is None:
            try:
                writer = glacier_secret_writer
            except ImportError:
                raise ConnectorError("Glacier's keychain store is unavailable; OAuth tokens were not saved.") from None
        try:
            writer(name, value)
        except Exception:
            raise ConnectorError("Glacier could not save the refreshed Jobber token in its keychain.") from None

    def refresh_access_token(self) -> None:
        """Refresh Jobber OAuth credentials, preserving rotated refresh tokens."""
        client_id = self._secret_resolver(self.client_id_secret)
        client_secret = self._secret_resolver(self.client_secret_secret)
        refresh_token = self._secret_resolver(self.refresh_token_secret)
        if not client_id or not client_secret or not refresh_token:
            raise ConnectorError("Jobber access expired; save its OAuth client ID, client secret, and refresh token in Glacier.")
        response = self._request(
            "POST", "https://api.getjobber.com/api/oauth/token",
            headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
            form_body={"client_id": client_id, "client_secret": client_secret, "grant_type": "refresh_token", "refresh_token": refresh_token},
            auth_post=True,
        )
        try:
            payload = response.json()
            new_access = payload["access_token"]
            new_refresh = payload.get("refresh_token", refresh_token)
        except (ValueError, KeyError, TypeError):
            raise ConnectorError("Jobber did not return refreshed OAuth credentials.") from None
        self._write_secret(self._secret_name, new_access)
        if new_refresh != refresh_token:
            self._write_secret(self.refresh_token_secret, new_refresh)
        self._access_token = new_access

    def graphql(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self._credential()}",
            "X-JOBBER-GRAPHQL-VERSION": self.api_version,
            "Content-Type": "application/json",
        }
        try:
            return self._graphql(JOBBER_GRAPHQL_URL, headers, query, variables)
        except UnauthorizedError:
            self.refresh_access_token()
            headers["Authorization"] = f"Bearer {self._credential()}"
            return self._graphql(JOBBER_GRAPHQL_URL, headers, query, variables)

    def test_connection(self) -> dict[str, Any]:
        result = self.graphql("query ConnectionCheck { account { id name } }")
        account = result.get("account") or {}
        if not account.get("id"):
            raise ConnectorError("Jobber did not return the connected account.")
        return {"connected": True, "account": account.get("name", "(name unavailable)")}

    def get_jobs(self, *, page_size: int = 50, max_pages: int = 100) -> list[dict[str, Any]]:
        page_size = min(100, max(1, page_size))
        rows: list[dict[str, Any]] = []
        cursor: str | None = None
        for _ in range(max_pages):
            query = "query ReadJobs($first: Int!, $after: String) { jobs(first: $first, after: $after) { nodes { id jobNumber title } pageInfo { hasNextPage endCursor } } }"
            data = self.graphql(query, {"first": page_size, "after": cursor})
            connection = data.get("jobs") or {}
            rows.extend(connection.get("nodes") or [])
            page = connection.get("pageInfo") or {}
            if not page.get("hasNextPage"):
                return rows
            next_cursor = page.get("endCursor")
            if not next_cursor or next_cursor == cursor:
                raise ConnectorError("Jobber returned an invalid pagination cursor.")
            cursor = next_cursor
        raise ConnectorError("Jobber read stopped at the configured page limit.")


class ShipStationClient(ReadOnlyClient):
    def __init__(self, *, api_key: str | None = None, secret_name: str = "shipstation_api_key", **kwargs: Any):
        kwargs.setdefault("request_interval", 0.31)
        super().__init__(secret_name=secret_name, api_key=api_key, **kwargs)

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return self._json(self._request("GET", SHIPSTATION_API_URL + path, headers={"API-Key": self._credential(), "Accept": "application/json"}, params=params))

    def test_connection(self) -> dict[str, Any]:
        response = self._get("/shipments", {"page": 1, "page_size": 1})
        if not isinstance(response.get("shipments"), list):
            raise ConnectorError("ShipStation did not return a readable shipments list.")
        return {"connected": True, "shipments_readable": True}

    def get_shipments(self, *, page_size: int = 100, max_pages: int = 100, **filters: Any) -> list[dict[str, Any]]:
        page_size = min(500, max(1, page_size))
        max_pages = min(max_pages, max(1, 10_000 // page_size))
        page = 1
        rows: list[dict[str, Any]] = []
        for _ in range(max_pages):
            response = self._get("/shipments", {**filters, "page": page, "page_size": page_size})
            batch = response.get("shipments") or []
            rows.extend(batch)
            total_pages = response.get("pages")
            if not batch or (total_pages is not None and page >= int(total_pages)) or len(batch) < page_size:
                return rows
            page += 1
        raise ConnectorError("ShipStation read stopped at the configured page limit.")


class ShopifyClient(ReadOnlyClient):
    def __init__(self, shop: str, *, access_token: str | None = None, secret_name: str = "shopify_admin_access_token", client_id_secret: str = "shopify_client_id", client_secret_secret: str = "shopify_client_secret", secret_writer: Any = None, api_version: str = SHOPIFY_API_VERSION, **kwargs: Any):
        kwargs.setdefault("request_interval", 0.1)
        super().__init__(secret_name=secret_name, access_token=access_token, **kwargs)
        shop = shop.strip().lower()
        if not shop.endswith(".myshopify.com") or "/" in shop:
            raise ValueError("Shopify shop must be the store's *.myshopify.com domain.")
        self.shop = shop
        self.api_version = api_version
        self.client_id_secret = client_id_secret
        self.client_secret_secret = client_secret_secret
        self._secret_writer = secret_writer
        self._force_client_credentials = False

    def _credential(self) -> str:
        if self._access_token and not self._force_client_credentials:
            return self._access_token
        if not self._force_client_credentials:
            try:
                saved = self._secret_resolver(self._secret_name)
            except Exception:
                saved = None
            if saved:
                return saved
        try:
            client_id = self._secret_resolver(self.client_id_secret)
            client_secret = self._secret_resolver(self.client_secret_secret)
        except Exception:
            client_id = client_secret = None
        if not client_id or not client_secret:
            return super()._credential()
        response = self._request(
            "POST", f"https://{self.shop}/admin/oauth/access_token",
            headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
            form_body={"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret},
            auth_post=True,
        )
        try:
            token = response.json()["access_token"]
        except (ValueError, KeyError, TypeError):
            raise ConnectorError("Shopify did not return an Admin API access token.") from None
        self._access_token = token
        self._force_client_credentials = False
        writer = self._secret_writer
        if writer is None:
            try:
                writer = glacier_secret_writer
            except ImportError:
                raise ConnectorError("Glacier's keychain store is unavailable; Shopify token was not saved.") from None
        try:
            writer(self._secret_name, token)
        except Exception:
            raise ConnectorError("Glacier could not save the Shopify token in its keychain.") from None
        return token

    def graphql(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"https://{self.shop}/admin/api/{self.api_version}/graphql.json"
        headers = {"X-Shopify-Access-Token": self._credential(), "Content-Type": "application/json"}
        try:
            return self._graphql(url, headers, query, variables)
        except UnauthorizedError:
            self._access_token = None
            self._force_client_credentials = True
            headers["X-Shopify-Access-Token"] = self._credential()
            return self._graphql(url, headers, query, variables)

    def test_connection(self) -> dict[str, Any]:
        data = self.graphql("query ConnectionCheck { shop { name myshopifyDomain } }")
        shop = data.get("shop") or {}
        if not shop.get("myshopifyDomain"):
            raise ConnectorError("Shopify did not return the connected store.")
        return {"connected": True, "shop": shop.get("myshopifyDomain"), "name": shop.get("name", "(name unavailable)")}

    def get_products(self, *, page_size: int = 50, max_pages: int = 100) -> list[dict[str, Any]]:
        page_size = min(250, max(1, page_size))
        rows: list[dict[str, Any]] = []
        cursor: str | None = None
        query = "query ReadProducts($first: Int!, $after: String) { products(first: $first, after: $after) { edges { node { id title handle vendor productType } cursor } pageInfo { hasNextPage endCursor } } }"
        for _ in range(max_pages):
            data = self.graphql(query, {"first": page_size, "after": cursor})
            connection = data.get("products") or {}
            rows.extend(edge.get("node") or {} for edge in connection.get("edges") or [])
            page = connection.get("pageInfo") or {}
            if not page.get("hasNextPage"):
                return rows
            next_cursor = page.get("endCursor")
            if not next_cursor or next_cursor == cursor:
                raise ConnectorError("Shopify returned an invalid pagination cursor.")
            cursor = next_cursor
        raise ConnectorError("Shopify read stopped at the configured page limit.")


class ApifyClient(ReadOnlyClient):
    def __init__(self, *, api_token: str | None = None, secret_name: str = "apify_api_token", **kwargs: Any):
        kwargs.setdefault("request_interval", 0.1)
        super().__init__(secret_name=secret_name, access_token=api_token, **kwargs)

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return self._json(self._request("GET", APIFY_API_URL + path, headers={"Authorization": f"Bearer {self._credential()}", "Accept": "application/json"}, params=params))

    def _get_response(self, path: str, params: dict[str, Any] | None = None) -> httpx.Response:
        return self._request("GET", APIFY_API_URL + path, headers={"Authorization": f"Bearer {self._credential()}", "Accept": "application/json"}, params=params)

    def test_connection(self) -> dict[str, Any]:
        response = self._get("/users/me")
        user = response.get("data") or response
        if not user.get("id"):
            raise ConnectorError("Apify did not return the connected account.")
        return {"connected": True, "username": user.get("username", "(username unavailable)")}

    def get_dataset_items(self, dataset_id: str, *, page_size: int = 100, max_pages: int = 100) -> list[dict[str, Any]]:
        if not dataset_id or "/" in dataset_id:
            raise ValueError("A dataset ID is required.")
        page_size = min(1000, max(1, page_size))
        offset = 0
        rows: list[dict[str, Any]] = []
        for _ in range(max_pages):
            response = self._get_response(f"/datasets/{quote(dataset_id, safe='')}/items", {"format": "json", "limit": page_size, "offset": offset})
            batch = self._json(response)
            if not isinstance(batch, list):
                raise ConnectorError("Apify returned an unexpected dataset response.")
            rows.extend(batch)
            total = response.headers.get("X-Apify-Pagination-Total")
            if (total is not None and offset + len(batch) >= int(total)) or not batch or len(batch) < page_size:
                return rows
            offset += len(batch)
        raise ConnectorError("Apify read stopped at the configured page limit.")
