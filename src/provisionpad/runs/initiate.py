import platform
import sys
import os
import json
from provisionpad.aws.aws_ec2 import AWSec2Funcs
from provisionpad.aws.aws_iam import AWSiamFuncs
from provisionpad.aws.aws_sts import AWSstsFuncs
from provisionpad.db.database import load_database, save_database
from provisionpad.runs.create_vpc import create_vpc

def initiate():

    DB = load_database()

    if platform.python_version()[0] == '2':
        input = raw_input

    home = os.path.expanduser("~")
    env_dir = os.path.join(home, '.provisionpad') 
    if not os.path.isdir(env_dir):
        os.mkdir(env_dir)
    env_var_path = os.path.join(env_dir, 'env_variable.json')
    if os.path.isfile(env_var_path):
        print ('the env variable file already exists')
        sys.exit('to be completed later')

    env_vars = {}
    print ('Initiating a new ppad environment')
    print ('  You can find aws access keys under user tab (top third from right)')
    print ('  My security credentials for the root info or under IAM users section')
    print ('  For more information please visit: https://docs.aws.amazon.com/general/latest/gr/aws-sec-cred-types.html')
    access_key = input('Please enter your aws access key ID: ')
    env_vars['access_key'] = str(access_key).strip()
    if not env_vars['access_key']:
        print ('Invalid input')
        sys.exit()
    secret_key = input('Please enter your aws secret access key: ')
    env_vars['secret_key'] = str(secret_key).strip()
    if not env_vars['secret_key']:
        print ('Invalid input')
        sys.exit()
    your_name  = input('Please enter the name you want to be associated with the env: ')
    env_vars['your_name'] = ''.join([x.strip().upper() for x in your_name.split(' ')] )
    if not env_vars['your_name']:
        print ('Invalid input')
        sys.exit()
    env_vars['your_email'] = input('Please enter the email you want to be associated with the env: ')
    print ('\n\n')
    print ('NOte: AMI (Image) should be in the same defined aws region')
    print ('Otherwise you will encounter errors later on')
    env_vars['aws_region'] = input ('Please enter your aws region. If nothing entered us-east-2 would be used as default')
    if not env_vars['aws_region']:
        env_vars['aws_region'] = 'us-east-2'
    env_vars['aws_ami'] = input ('Please enter your aws ami. If nothing entered default Ubuntu 18 will be used')
    if not env_vars['aws_ami']:
        env_vars['aws_ami'] = 'ami-00df714b389c23925'

    key_pair_name = 'ec2_keypair_{0}_{1}.pem'.format(env_vars['your_name'], env_vars['aws_region']) 
    key_pair_path = os.path.join(env_dir, key_pair_name)

    env_vars['key_pair_name'] = key_pair_name
    env_vars['key_pair_path'] = key_pair_path

    env_vars['vpc_name'] = '{0}_VPC'.format(env_vars['your_name']) 

    role_name   = [env_vars['your_name'] ]
    policies = ['S3FULL']
    role_name.extend(policies)
    role_names = ''.join(role_name)

    env_vars['policy'] = policies
    env_vars['role_name'] = role_names

    env_vars['HOME'] = home

    create_vpc(env_vars, DB)

    awsec2f = AWSec2Funcs(env_vars['aws_region'], env_vars['access_key'], env_vars['secret_key'])
    awsstsf = AWSstsFuncs(env_vars['aws_region'], env_vars['access_key'], env_vars['secret_key'])
    awsiamf = AWSiamFuncs(env_vars['aws_region'], env_vars['access_key'], env_vars['secret_key'])

    if not os.path.isfile(env_vars['key_pair_path']):
        if not awsec2f.check_key_pair(env_vars['key_pair_name']):
            print ('creating key pair')
            with open(env_vars['key_pair_path'], 'w') as f:
                key_pair = str(awsec2f.create_key_pair(key_pair_name))
                f.write(key_pair)
        else:
            print ('we can find the pem key in your laptop but the bublic key is not on aws')
            sys.exit()
    else:
        print ('the key pair exists')

    account_id = awsstsf.get_account_id()
    policy_attach = []
    for policy in env_vars['policy']:
        policy_arn = 'arn:aws:iam::{0}:policy/{1}'.format(account_id, policy ) 
        if not awsiamf.check_policy_exists(policy_arn):
            if policy == 'S3FULL':
                awsiamf.ec2_policy_access_full(policy)
                policy_attach.append(policy_arn)
            else:
                print ('the policy {0} not implemented yet'.format(policy))
        else:
            print ('the policy {0} exists'.format(policy))
            policy_attach.append(policy_arn)
    
    role_arn = 'arn:aws:iam::{0}:role/{1}'.format(account_id, env_vars['role_name'])

    if not awsiamf.check_role_exists(env_vars['role_name']):
        awsiamf.create_role_for_ec2(env_vars['role_name'])

    if awsiamf.check_role_exists(env_vars['role_name'], 1, 5):
        for policy in policy_attach:
            print ('attaching policy arn: {0}'.format(policy))
            awsiamf.attach_policy_to_role(env_vars['role_name'], policy)
    else:
        print (' was not able to find the role')
        sys.exit()
    

    with open(env_var_path, 'w') as f:
        json.dump(env_vars, f, indent=4)


# export aws_access_key_id="AKIAJD3I34GBJGGM5DMQ"
# export aws_secret_access_key="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"


    # region = os.environ['aws_region']
    # access_key = os.environ['aws_access_key_id']
    # secret_key = os.environ['aws_secret_access_key']


    # role_arn = 'ec2s3accessful'
    # role_arn = 'amirtestdd'

    # awsiamf = AWSiamFuncs(region, access_key, secret_key)

    # if not awsiamf.check_role_exists(role_arn):
    #     awsiamf.create_role_for_ec2(role_arn)

    # try: 
    #     awsiamf.check_role_exists(role_arn, 1, 3)
    #     for policy in policy_attach:
    #         awsiamf.attach_policy_to_role(env_vars['role_name'], policy)
    # except:
    #     print (' was not able to find the role')
    #     sys.exit()

    # # print (awsiamf.check_role_exists(role_arn, 1, 3) )
    # # # # awsf.attach_policy_to_role('amir_role',policy_arn)


     