# ssm

> Python CLI that leverages SSM's capability to provide an SSH access to EC2 instances.

## Prerequisites
* [python](https://www.python.org/) >= 3.3
* [session-manager-plugin](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html)

## Usage
Run

```bash
pipenv install
pipenv shell
```

to have the virtualenv activated for some profit.

In order to connect to a running EC2 instance, you must provide valid AWS credentials, e.g. by specifying the profile:

```bash
AWS_PROFILE=some-profile "./ssm.py login" 
```
