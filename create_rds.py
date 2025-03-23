import boto3
from botocore.exceptions import ClientError

AWS_REGION = 'us-east-1'
RDS_IDENTIFIER = 'parkingdb-instance'
DB_NAME = 'x23417498_db'
MASTER_USERNAME = 'admin'
MASTER_PASSWORD = 'zxcvbnm1234567'
INSTANCE_CLASS = 'db.t3.micro'
ENGINE = 'mysql'
ENGINE_VERSION = '8.0.36'
STORAGE = 20

# Initialize RDS client using the default profile
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
            VpcSecurityGroupIds=['sg-07220fa92a4ea61b0'],
            PubliclyAccessible=True,
            MultiAZ=False,
            StorageType='gp2',
            BackupRetentionPeriod=7,
            Tags=[
                {'Key': 'Name', 'Value': 'ParkingDB'},
                {'Key': 'Project', 'Value': 'ParkingProject'},
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
        print(f"Configuration: DB Name={DB_NAME}, Username={MASTER_USERNAME}, Password={MASTER_PASSWORD}, Region={AWS_REGION}, Endpoint={endpoint}")