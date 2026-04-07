import argparse
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError, NoCredentialsError

import ssm


def _client_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": code}}, "DescribeInstances")


def _empty_namespace() -> argparse.Namespace:
    return argparse.Namespace()


class TestGetRunningInstances:
    def test_returns_flattened_instances(self) -> None:
        # given
        ec2 = MagicMock()
        ec2.describe_instances.return_value = {
            "Reservations": [
                {"Instances": [{"InstanceId": "i-1"}, {"InstanceId": "i-2"}]},
                {"Instances": [{"InstanceId": "i-3"}]},
            ]
        }

        # when
        result = ssm.get_running_instances(ec2)

        # then
        assert [i["InstanceId"] for i in result] == ["i-1", "i-2", "i-3"]
        ec2.describe_instances.assert_called_once_with(
            Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
        )

    def test_returns_empty_list_when_no_reservations(self) -> None:
        # given
        ec2 = MagicMock()
        ec2.describe_instances.return_value = {"Reservations": []}

        # when
        result = ssm.get_running_instances(ec2)

        # then
        assert result == []

    def test_exits_on_auth_failure(self) -> None:
        # given
        ec2 = MagicMock()
        ec2.describe_instances.side_effect = _client_error("AuthFailure")

        # when / then
        with pytest.raises(SystemExit, match="Not authorized"):
            ssm.get_running_instances(ec2)

    def test_exits_on_other_client_error(self) -> None:
        # given
        ec2 = MagicMock()
        ec2.describe_instances.side_effect = _client_error("Throttling")

        # when / then
        with pytest.raises(SystemExit, match="Throttling"):
            ssm.get_running_instances(ec2)

    def test_exits_on_missing_credentials(self) -> None:
        # given
        ec2 = MagicMock()
        ec2.describe_instances.side_effect = NoCredentialsError()

        # when / then
        with pytest.raises(SystemExit, match="No AWS credentials"):
            ssm.get_running_instances(ec2)


class TestOpenInstanceConnection:
    def test_spawns_aws_ssm_session(self) -> None:
        # given
        instance_id = "i-abc123"

        # when
        with patch("ssm.pty.spawn") as spawn:
            ssm.open_instance_connection(instance_id)

        # then
        spawn.assert_called_once_with(["aws", "ssm", "start-session", "--target", instance_id])


class TestInstanceLogin:
    def test_shows_menu_with_running_instances(self) -> None:
        # given
        instances = [
            {"InstanceId": "i-1", "PrivateDnsName": "host-1"},
            {"InstanceId": "i-2", "PrivateDnsName": "host-2"},
        ]

        # when
        with (
            patch("ssm.boto3.client"),
            patch.object(ssm, "get_running_instances", return_value=instances),
            patch.object(ssm, "CursesMenu") as menu_cls,
        ):
            menu = menu_cls.return_value
            ssm.instance_login(_empty_namespace())

        # then
        assert menu.append_item.call_count == 2
        menu.show.assert_called_once()

    def test_prints_message_when_no_instances(self, capsys: pytest.CaptureFixture[str]) -> None:
        # given / when
        with (
            patch("ssm.boto3.client"),
            patch.object(ssm, "get_running_instances", return_value=[]),
            patch.object(ssm, "CursesMenu") as menu_cls,
        ):
            ssm.instance_login(_empty_namespace())

        # then
        assert "No running instances" in capsys.readouterr().out
        menu_cls.assert_not_called()


class TestBuildParser:
    def test_login_subcommand_dispatches_to_instance_login(self) -> None:
        # given
        parser = ssm.build_parser()

        # when
        args = parser.parse_args(["login"])

        # then
        assert args.func is ssm.instance_login

    def test_no_command_has_no_func(self) -> None:
        # given
        parser = ssm.build_parser()

        # when
        args = parser.parse_args([])

        # then
        assert not hasattr(args, "func")
