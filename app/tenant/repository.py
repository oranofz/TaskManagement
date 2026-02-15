"""Tenant repository for data access."""
from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.tenant.domain.models import Tenant
from loguru import logger


class TenantRepository:
    """Repository for tenant data access."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository."""
        self.session = session

    async def get_tenant_by_id(self, tenant_id: UUID) -> Optional[Tenant]:
        """Get tenant by ID."""
        result = await self.session.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_tenant_by_subdomain(self, subdomain: str) -> Optional[Tenant]:
        """Get tenant by subdomain."""
        result = await self.session.execute(
            select(Tenant).where(Tenant.subdomain == subdomain)
        )
        return result.scalar_one_or_none()

    async def create_tenant(self, tenant: Tenant) -> Tenant:
        """Create new tenant."""
        self.session.add(tenant)
        await self.session.commit()
        await self.session.refresh(tenant)
        logger.info(f"Tenant created: {tenant.id}")
        return tenant

    async def update_tenant(self, tenant: Tenant) -> Tenant:
        """Update tenant."""
        await self.session.commit()
        await self.session.refresh(tenant)
        logger.info(f"Tenant updated: {tenant.id}")
        return tenant

