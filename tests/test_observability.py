"""Tests for distributed tracing with OpenTelemetry."""

class TestTracingModule:
    """Test OpenTelemetry tracing functionality."""

    def test_extract_subdomain_tenant(self):
        """Test subdomain extraction from various host patterns."""
        from app.shared.middleware.tenant_resolver import extract_subdomain

        # Valid subdomain
        assert extract_subdomain("tenant1.example.com") == "tenant1"
        assert extract_subdomain("tenant1.example.com:8000") == "tenant1"
        assert extract_subdomain("mycompany.api.example.com") == "mycompany"

        # No subdomain (localhost)
        assert extract_subdomain("localhost") is None
        assert extract_subdomain("localhost:8000") is None
        assert extract_subdomain("127.0.0.1") is None
        assert extract_subdomain("127.0.0.1:8000") is None

        # Reserved subdomains
        assert extract_subdomain("www.example.com") is None
        assert extract_subdomain("api.example.com") is None
        assert extract_subdomain("admin.example.com") is None

        # Not enough parts (no subdomain)
        assert extract_subdomain("example.com") is None

    def test_standard_response_success(self):
        """Test StandardResponse success creation."""
        from app.shared.response import create_success_response

        data = {"id": "123", "name": "Test"}
        response = create_success_response(data)

        assert response.success is True
        assert response.data == data
        assert response.error is None
        assert "timestamp" in response.metadata

    def test_standard_response_error(self):
        """Test StandardResponse error creation."""
        from app.shared.response import create_error_response

        response = create_error_response(
            error_message="Something went wrong",
            error_code="ERROR_CODE"
        )

        assert response.success is False
        assert response.data is None
        assert response.error is not None
        assert response.error.message == "Something went wrong"
        assert response.error.code == "ERROR_CODE"

    def test_standard_response_pagination(self):
        """Test StandardResponse with pagination."""
        from app.shared.response import create_paginated_response

        items = [{"id": 1}, {"id": 2}, {"id": 3}]
        response = create_paginated_response(
            items=items,
            page=1,
            page_size=10,
            total_items=25
        )

        assert response.success is True
        assert response.data == items
        assert "pagination" in response.metadata

        pagination = response.metadata["pagination"]
        assert pagination["page"] == 1
        assert pagination["page_size"] == 10
        assert pagination["total_items"] == 25
        assert pagination["total_pages"] == 3
        assert pagination["has_next"] is True
        assert pagination["has_previous"] is False


class TestTenantResolver:
    """Tests for tenant resolver middleware."""

    def test_reserved_subdomain_extraction(self):
        """Test that reserved subdomains are not treated as tenant identifiers."""
        from app.shared.middleware.tenant_resolver import extract_subdomain

        reserved = ["www", "api", "app", "admin", "mail", "smtp", "ftp"]
        for subdomain in reserved:
            result = extract_subdomain(f"{subdomain}.example.com")
            assert result is None, f"Expected None for reserved subdomain '{subdomain}'"

    def test_valid_subdomain_extraction(self):
        """Test valid tenant subdomain extraction."""
        from app.shared.middleware.tenant_resolver import extract_subdomain

        valid_tenants = ["acme", "company1", "tenant-a", "org123"]
        for tenant in valid_tenants:
            result = extract_subdomain(f"{tenant}.example.com")
            assert result == tenant.lower(), f"Expected '{tenant.lower()}' for subdomain '{tenant}'"

