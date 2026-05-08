import os
import boto3
from botocore.exceptions import ClientError

AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
RDS_IDENTIFIER = os.environ.get('RDS_IDENTIFIER')           
DB_NAME = os.environ.get('DB_NAME')                        
MASTER_USERNAME = os.environ.get('MASTER_USERNAME')
MASTER_PASSWORD = os.environ.get('MASTER_PASSWORD')
INSTANCE_CLASS = os.environ.get('INSTANCE_CLASS', 'db.t3.micro')
ENGINE = os.environ.get('ENGINE', 'mysql')
ENGINE_VERSION = os.environ.get('ENGINE_VERSION', '8.0.36')
STORAGE = int(os.environ.get('STORAGE', 20))
VPC_SECURITY_GROUP_IDS = os.environ.get('VPC_SECURITY_GROUP_IDS', 'sg-07220fa92a4ea61b0').split(',')

# Initialize RDS client using the configured region
rds_client = boto3.client('rds', region_name=AWS_REGION)

def create_rds_instance():
    try:
        print(f"Creating RDS instance: {RDS_IDENTIFIER}")
        response = rds_client.create_db_instance(
            DBInstanceIdentifier=RDS_IDENTIFIER,
            DBName=DB_NAME,
            MasterUsername=MASTER_USERNAME,
            MasterUserPassword=MASTER_PASSWORD,
            DBInstanceClass=INSTANCE_CLASS,
            Engine=ENGINE,
            EngineVersion=ENGINE_VERSION,
            AllocatedStorage=STORAGE,
            VpcSecurityGroupIds=VPC_SECURITY_GROUP_IDS,
            PubliclyAccessible=True,
            MultiAZ=False,
            StorageType='gp2',
            BackupRetentionPeriod=7,
            Tags=[
                {'Key': 'Name', 'Value': os.environ.get('TAG_NAME', 'ParkingDB')},
                {'Key': 'Project', 'Value': os.environ.get('TAG_PROJECT', 'ParkingProject')},
            ]
        )
        print(f"DB instance created with identifier: {response['DBInstance']['DBInstanceIdentifier']}")
        # Wait for the instance to be available
        waiter = rds_client.get_waiter('db_instance_available')
        waiter.wait(DBInstanceIdentifier=RDS_IDENTIFIER)
        # Get the endpoint
        instance = rds_client.describe_db_instances(DBInstanceIdentifier=RDS_IDENTIFIER)
        endpoint = instance['DBInstances'][0]['Endpoint']['Address']
        print(f"RDS Endpoint: {endpoint}")
        return endpoint
    except ClientError as e:
        print(f"Error creating RDS instance: {e}")
        return None

if __name__ == "__main__":
    endpoint = create_rds_instance()
    if endpoint:
        print(f"Configuration: DB Name=<hidden>, Username=<hidden>, Password=<hidden>, Region={AWS_REGION}, Endpoint={endpoint}")
