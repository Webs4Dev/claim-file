"""Create a reviewer account. Reviewers cannot sign up through the API.

    venv/bin/python -m scripts.create_reviewer

The password is read with getpass so it never appears in shell history.
"""

from getpass import getpass

from auth.store import create_user


def main() -> None:
    email = input("Reviewer email: ")
    name = input("Reviewer name: ")
    password = getpass("Password (min 8 characters): ")

    if getpass("Repeat password: ") != password:
        raise SystemExit("Passwords do not match.")

    try:
        user = create_user(email, name, password, "reviewer")
    except ValueError as error:
        raise SystemExit(str(error)) from error

    print(f"Created reviewer {user.name} <{user.email}>.")


if __name__ == "__main__":
    main()
