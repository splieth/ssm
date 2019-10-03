#!/usr/bin/env python

import argparse
from botocore.exceptions import ClientError
import boto3
from termcolor import cprint
import sys
from cursesmenu import *
from cursesmenu.items import *
import pty

EC2_CLIENT = boto3.client('ec2')


def get_instances():
    instances = []
    try:
        instances = EC2_CLIENT.describe_instances(
            Filters=[
                {
                    'Name': 'instance-state-name',
                    'Values': [
                        'running'
                    ]
                }
            ]
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'AuthFailure':
            print('Not authorized')
            sys.exit(1)
        else:
            print(e.response['Error']['Code'])

    return instances


def open_instance_connection(instance_id):
    pty.spawn(["aws", "ssm", "start-session", "--target", instance_id])


def instance_login(_args):
    instances = get_instances()
    services = []
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            for tag in instance['Tags']:
                if tag['Key'] == 'service':
                    if tag['Value'] not in services:
                        services.append(tag['Value'])

    menu = CursesMenu("All instances", "Server")

    for one_service in services:
        for reservation in instances['Reservations']:
            for instance in reservation['Instances']:
                for tag in instance['Tags']:
                    if tag['Key'] == 'service':
                        if one_service == tag['Value']:
                            function_item = FunctionItem(
                                instance['InstanceId'] + ' - ' + tag['Value'],
                                open_instance_connection, [instance['InstanceId']], should_exit=True
                            )
                            menu.append_item(function_item)
    menu.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Open SSH connection to EC2 instances via SSM')
    subparsers = parser.add_subparsers(help='<subcommand> help')

    parser_login_command = subparsers.add_parser('login', help='Login to certain instance')
    parser_login_command.set_defaults(func=instance_login)

    args = parser.parse_args()

    try:
        args.func(args)
    except AttributeError:
        parser.print_help()
