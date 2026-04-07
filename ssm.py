#!/usr/bin/env python
"""CLI to open an SSH-like session to EC2 instances via AWS SSM."""

import argparse
import pty
import sys
from typing import Any

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from cursesmenu import CursesMenu
from cursesmenu.items import FunctionItem


def get_running_instances(ec2_client: Any) -> list[dict[str, Any]]:
    """Return a list of running EC2 instances."""
    try:
        response = ec2_client.describe_instances(
            Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
        )
    except NoCredentialsError:
        sys.exit("No AWS credentials found.")
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "AuthFailure":
            sys.exit("Not authorized.")
        sys.exit(f"AWS error: {code}")

    return [
        instance
        for reservation in response["Reservations"]
        for instance in reservation["Instances"]
    ]


def open_instance_connection(instance_id: str) -> None:
    """Start an SSM session against the given instance."""
    pty.spawn(["aws", "ssm", "start-session", "--target", instance_id])


def instance_login(_args: argparse.Namespace) -> None:
    ec2_client = boto3.client("ec2")
    instances = get_running_instances(ec2_client)

    if not instances:
        print("No running instances found.")
        return

    menu = CursesMenu("All instances", "Server")
    for instance in instances:
        label = f"{instance['InstanceId']} | {instance['PrivateDnsName']}"
        menu.append_item(
            FunctionItem(
                label,
                open_instance_connection,
                [instance["InstanceId"]],
                should_exit=True,
            )
        )
    menu.show()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Open an SSH connection to EC2 instances via SSM.")
    subparsers = parser.add_subparsers(dest="command")

    login_parser = subparsers.add_parser("login", help="Login to an instance.")
    login_parser.set_defaults(func=instance_login)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
