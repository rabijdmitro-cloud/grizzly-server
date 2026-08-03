from __future__ import annotations

from database import add_user, init_db, list_users


def main() -> None:
    init_db()

    users = list_users()
    if not users:
        add_user("Admin", "admin@example.com")
        users = list_users()

    print("Users in database:")
    for user_id, name, email in users:
        print(f"- {user_id}: {name} <{email}>")


if __name__ == "__main__":
    main()
