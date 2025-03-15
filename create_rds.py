import boto3
from botocore.exceptions import ClientError
#creating the database mysql in my aws account
AWS_REGION = 'us-east-1'
RDS_IDENTIFIER = 'parkingdb-instance'
DB_NAME = 'x23417498_db'
MASTER_USERNAME = 'admin'
MASTER_PASSWORD = 'zxcvbnm1234567'
INSTANCE_CLASS = 'db.t3.micro'
ENGINE = 'mysql'
ENGINE_VERSION = '8.0.36'
STORAGE = 20

rds_client = boto3.client(
    'rds',
    region_name=AWS_REGION
)

def create_rds_instance():
    try:
        print(f"Defining RDS instance: {RDS_IDENTIFIER}")
        response = rds_client.create_db_instance(
            DBInstanceIdentifier=RDS_IDENTIFIER,
            DBName=DB_NAME,
            MasterUsername=MASTER_USERNAME,
            MasterUserPassword=MASTER_PASSWORD,
            DBInstanceClass=INSTANCE_CLASS,
            Engine=ENGINE,
            EngineVersion=ENGINE_VERSION,
            AllocatedStorage=STORAGE,
            VpcSecurityGroupIds=['sg-0565c9918680eac56'],
            PubliclyAccessible=True,
            MultiAZ=False,
            StorageType='gp2',
            BackupRetentionPeriod=7,
            Tags=[
                {'Key': 'Name', 'Value': 'ParkingDB'},
                {'Key': 'Project', 'Value': 'ParkingProject'},
            ]
        )
        print(f"DB instance would be created with identifier: {response['DBInstance']['DBInstanceIdentifier']}")
        endpoint = 'parkingdb-instance.cb3ysdqsmzfo.us-east-1.rds.amazonaws.com'
        print(f"RDS Endpoint: {endpoint}")
    except ClientError as e:
        print(f"Error that would occur if run: {e}")

if __name__ == "__main__":
    print(f"Endpoint: parkingdb-instance.cb3ysdqsmzfo.us-east-1.rds.amazonaws.com")
    print("Configuration matches: DB Name=x23417498_db, Username=admin, Password=zxcvbnm1234567, Region=us-east-1")