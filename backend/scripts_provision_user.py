"""Provision a user and company-scoped role. No public self-registration endpoint exists."""
import argparse, asyncio
from datetime import datetime, timezone
from getpass import getpass
from uuid import UUID
from sqlalchemy import select
from app.models.auth import User, CompanyMembership
from app.platform.database.session import get_session_factory, dispose_database
from app.services.auth.security import hash_password

async def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--email",required=True); parser.add_argument("--display-name",required=True)
    parser.add_argument("--company-id",required=True); parser.add_argument("--role",choices=["ANALYST","REVIEWER","ADMIN"],required=True)
    args=parser.parse_args(); company_id=UUID(args.company_id); password=getpass("Password (min. 12 characters): ")
    async with get_session_factory()() as session:
        user=await session.scalar(select(User).where(User.email==args.email.strip().lower()))
        if user is None:
            user=User(email=args.email.strip().lower(),display_name=args.display_name,
                      password_hash=hash_password(password),is_active=True,created_at=datetime.now(timezone.utc))
            session.add(user); await session.flush()
        membership=await session.scalar(select(CompanyMembership).where(
            CompanyMembership.user_id==user.id,CompanyMembership.company_id==company_id))
        if membership is None:
            membership=CompanyMembership(user_id=user.id,company_id=company_id,role=args.role,created_at=datetime.now(timezone.utc)); session.add(membership)
        else: membership.role=args.role
        await session.commit()
        print(f"Provisioned {user.email} ({user.id}) with {args.role} for company {company_id}")
    await dispose_database()

if __name__=="__main__": asyncio.run(main())
