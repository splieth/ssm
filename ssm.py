#!/usr/bin/env python

import argparse
from botocore.exceptions import ClientError
import boto3
from termcolor import cprint
import sys
from cursesmenu import *
from cursesmenu.items import *
import time
import os

SSM_CLIENT = boto3.client('ssm')
EC2_CLIENT = boto3.client('ec2')


def execute_ssm_command(command, document, instances_ids, tag_key, tag_value):
    try:
        res = SSM_CLIENT.send_command(
            InstanceIds=instances_ids,
            Targets=[
                {
                    'Key': 'tag:service',
                    'Values': [
                        tag_value
                    ]
                }
            ],
            DocumentName=document,
            Parameters={
                'commands': [
                    command
                ]
            }
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'AuthFailure':
            print('You are not authorized')
            sys.exit(1)
        else:
            print(e.response['Error']['Code'])
            sys.exit(1)

    return res['Command']['CommandId']


def ssm_command_results(cid):
    command_status = {'Commands': []}
    while not command_status['Commands']:
        command_status = SSM_CLIENT.list_commands(
            CommandId=cid,
            Filters=[
                {
                    'key': 'ExecutionStage',
                    'value': 'Complete'
                },
            ]
        )
        time.sleep(1)

    res = SSM_CLIENT.list_command_invocations(
        CommandId=cid,
        Details=True
    )

    error_command = False

    for invocation in res['CommandInvocations']:
        cprint('InstanceID: ' + invocation['InstanceId'], 'green', attrs=['bold'])
        for command_plugin in invocation['CommandPlugins']:
            cprint(command_plugin['Output'])
            if command_plugin['ResponseCode'] == 0:
                color = 'green'
            else:
                error_command = True
                color = 'red'
            cprint('ExitCode: ' + str(command_plugin['ResponseCode']) + ' Status: ' + invocation['Status'], color)

        print('\n')

    # If one command returns an error exit with a failure
    if error_command:
        sys.exit(1)


def list_instances():
    instances = get_instances()

    list = [instance for instance, reservation in instances['Reservations']]

    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            for tag in instance['Tags']:
                if tag['Key'] == 'service':
                    print(instance['InstanceId'] + ' - ' + tag['Value'])


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


def ssm_command(ssm_command_args):
    instances = ssm_command_args.instances.split(',') if len(ssm_command_args.instances) > 0 else []
    command_id = execute_ssm_command(ssm_command_args.command, ssm_command_args.document_name, instances, ssm_command_args.service)
    ssm_command_results(command_id)


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
                environment = next(tag for tag in instance['Tags'] if tag['Key'] == 'environment')['Value']
                for tag in instance['Tags']:
                    if tag['Key'] == 'service':
                        if one_service == tag['Value']:
                            function_item = FunctionItem(
                                instance['InstanceId'] + ' - ' + tag['Value'] + '-' + environment,
                                open_instance_connection, [instance['InstanceId']], should_exit=True
                            )
                            menu.append_item(function_item)
    menu.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run SSH commands via SSM')
    subparsers = parser.add_subparsers(help='sub-command help')

    parser_ssm_command = subparsers.add_parser('run', help='a help')
    parser_ssm_command.add_argument('-c', '--command', help='Removed command to execute', required=True)
    parser_ssm_command.add_argument('-i', '--instances', default=[], help='List of instances')
    parser_ssm_command.add_argument('-k', '--tag-key', default="service", help='Search for instances tagged with this key')
    parser_ssm_command.add_argument('-s', '--tag-value', default="UNUSED", help='Search for instances with that are tagged with this value')
    parser_ssm_command.add_argument('-d', '--document-name', default='AWS-RunShellScript', help='Define SSM document')
    parser_ssm_command.set_defaults(func=ssm_command)

    parser_list_command = subparsers.add_parser('list', help='List all running instances')
    parser_list_command.set_defaults(func=list_instances)

    parser_login_command = subparsers.add_parser('login', help='Login into certain instance')
    parser_login_command.set_defaults(func=instance_login)

    args = parser.parse_args()

    try:
        args.func(args)
    except AttributeError:
        parser.print_help()
