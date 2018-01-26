import names
import click
import boto3
import random
import requests
import json
import logging

from itertools import groupby

FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format=FORMAT)

logger = logging.getLogger(__name__)


@click.group()
@click.pass_context
def cli(ctx):
    ctx.obj = {}
    pass


@cli.command('generate-iam-users')
@click.option('--count', default=100)
def generate_iam_user(count):
    iam_client = boto3.client('iam')
    for index in range(0, count):
        try:
            first_name = names.get_first_name()
            last_name = names.get_last_name()

            print 'Creating user. username={}.{}'.format(first_name, last_name)

            iam_client.create_user(
                UserName='{}.{}'.format(first_name, last_name),
                Path='/evilcorp/'
            )
        except Exception as e:
            logger.error(e, exc_info=True)


@cli.command('generate-group-attachements')
def generate_group_attachements():
    iam_client = boto3.client('iam')

    groups = iam_client.list_groups()['Groups']
    users = list_users(PathPrefix='/evilcorp/')

    for user in users:
        try:
            group_num = random.randrange(0, len(groups))

            for _ in range(0, group_num):
                group_index = random.randrange(0, len(groups))
                group = groups[group_index]

                print 'Adding user to group. username={}, group_name={}'.format(user['UserName'], group['GroupName'])
                response = iam_client.add_user_to_group(
                    GroupName=group['GroupName'],
                    UserName=user['UserName']
                )
        except Exception as e:
            logger.error(e, exc_info=True)


@cli.command('delete-users')
def delete_users():
    iam_client = boto3.client('iam')
    for user in list_users(PathPrefix='/evilcorp/'):
        try:
            print 'Delete user. username={}'.format(user['UserName'])
            remove_user_from_group(user['UserName'])
            iam_client.delete_user(UserName=user['UserName'])
        except Exception as e:
            logger.error(e, exc_info=True)


@cli.command('generate-group-policy-attachements')
def generate_group_policy_attachements():
    iam_client = boto3.client('iam')
    policies = list(list_policies(PathPrefix='/'))

    attached_policy_count = random.randrange(0, 5)
    inline_policy_count = random.randrange(0, 5)

    for group in list_groups():
        for _ in range(0, attached_policy_count):
            try:
                policy_index = random.randrange(0, len(policies))

                policy_arn = policies[policy_index]['Arn']

                print 'Attaching policy to group. group_name={}, policy_arn={}'.format(group['GroupName'], policy_arn)
                response = iam_client.attach_group_policy(
                    GroupName=group['GroupName'],
                    PolicyArn=policy_arn
                )
            except Exception as e:
                logger.error(e, exc_info=True)


@cli.command('generate-user-policies')
@click.option('--skip-attached-policy', is_flag=True)
@click.option('--max-attached-policy-count', default=5)
@click.option('--max-inline-policy-count', default=5)
@click.option('--max-inline-policy-statement-count', default=2)
@click.option('--max-inline-policy-statement-action-count', default=5)
def generate_user_policies(
    max_attached_policy_count,
    skip_attached_policy,
    max_inline_policy_count,
    max_inline_policy_statement_count,
    max_inline_policy_statement_action_count,
):
    iam_client = boto3.client('iam')
    policies = list(list_policies(PathPrefix='/'))


    attached_policy_count = 0 if skip_attached_policy else random.randrange(0, max_attached_policy_count)
    inline_policy_count = random.randrange(0, max_inline_policy_count)

    for user in list_users(PathPrefix='/evilcorp/'):
        for _ in range(0, attached_policy_count):
            try:
                policy_index = random.randrange(0, len(policies))

                policy_arn = policies[policy_index]['Arn']

                print 'Attaching policy to user. user_name={}, policy_arn={}'.format(user['UserName'], policy_arn)
                response = iam_client.attach_user_policy(
                    UserName=user['UserName'],
                    PolicyArn=policy_arn
                )
            except Exception as e:
                logger.error(e, exc_info=True)

        for _ in range(0, inline_policy_count):
            try:
                statement_count = random.randrange(0, max_inline_policy_statement_count)
                action_count = random.randrange(0, max_inline_policy_statement_action_count)
                
                policy = generate_policy(
                    statement_count=max_inline_policy_statement_count,
                    action_count=max_inline_policy_statement_action_count
                )

                print 'Adding inline policy to user. user_name={}'.format(user['UserName'])
                response = iam_client.put_user_policy(
                    UserName=user['UserName'],
                    PolicyName='policy-{}'.format(_),
                    PolicyDocument=json.dumps(policy)
                )
            except Exception as e:
                logger.error(e, exc_info=True)


def generate_policy(statement_count, action_count):
    actions = get_all_iam_actions()

    policy = {
        'Version': '2012-10-17',
        'Statement': []
    }

    for _ in range(0, statement_count):
        statement = {
            'Effect': 'Allow',
            'Action': [],
            'Resource': '*'
        }
        policy['Statement'].append(statement)

        for _ in range(0, action_count):
            action_index = random.randrange(0, len(actions))
            action = actions[action_index]
            statement['Action'].append(action.full_name)

    return policy


# def group_actions(actions):
#     group = {}
#
#     actions =
#     for key, value in groupby(actions, lambda a: a.service):
#         group[key] = list(value)
#
#     return group


@click.pass_context
def get_all_iam_actions(ctx):
    if 'all_actions' in ctx.obj:
        return [Action.from_string(a) for a in ctx.obj['all_actions']]

    response = requests.get('https://raw.githubusercontent.com/rvedotrc/aws-iam-reference/master/all-actions.txt')

    ctx.obj['all_actions'] = response.text.splitlines()
    return [Action.from_string(a) for a in ctx.obj['all_actions']]


def remove_user_from_group(username):
    iam_client = boto3.client('iam')
    groups_response = iam_client.list_groups_for_user(
        UserName=username
    )

    for group in groups_response['Groups']:
        response = iam_client.remove_user_from_group(
            GroupName=group['GroupName'],
            UserName=username
        )


def list_groups(**kwargs):
    iam_client = boto3.client('iam')

    while True:
        response = iam_client.list_groups(**kwargs)

        for group in response['Groups']:
            yield group

        kwargs['Marker'] = response.get('Marker')
        if kwargs['Marker'] is None:
            break


def list_users(**kwargs):
    iam_client = boto3.client('iam')

    while True:
        response = iam_client.list_users(**kwargs)

        for user in response['Users']:
            yield user

        kwargs['Marker'] = response.get('Marker')
        if kwargs['Marker'] is None:
            break


def list_policies(**kwargs):
    iam_client = boto3.client('iam')

    while True:
        response = iam_client.list_policies(**kwargs)

        for policy in response['Policies']:
            yield policy

        kwargs['Marker'] = response.get('Marker')
        if kwargs['Marker'] is None:
            break


class Action(object):
    def __init__(self, service, action):
        self.service = service
        self.action = action

    @classmethod
    def from_string(cls, value):
        chunks = value.split(':')
        return cls(chunks[0], chunks[1])

    @property
    def full_name(self):
        return '{}:{}'.format(self.service, self.action)

    def __repr__(self):
        return 'Actions service<{}>, action<{}>'.format(self.service, self.action)


if __name__ == '__main__':
    cli()
