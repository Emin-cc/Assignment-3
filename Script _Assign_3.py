import boto3
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

# Prompt user for AWS setup (Access key, Security key, Region)
def setup_aws():
    print("AWS Configuration")
    access_key = input("Enter AWS Access Key (or leave blank to use AWS CLI profile): ")
    secret_key = input("Enter AWS Secret Key (or leave blank to use AWS CLI profile): ")
    region = input("Enter AWS Region (e.g., us-east-1): ") or "us-east-1"

    # Use user provided credentials or default session.
    if access_key and secret_key:
        session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
    else:
        session = boto3.Session(region_name=region)

    ec2 = session.client('ec2')
    cloudwatch = session.client('cloudwatch')
    return ec2, cloudwatch

# List of EC2 instances
def list_instances(ec2):
    response = ec2.describe_instances()
    instances = []
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instances.append({
                'InstanceId': instance['InstanceId'],
                'State': instance['State']['Name']
            })
    return instances

# Gets CPU utilization metrics
def get_cpu_utilization(cloudwatch, instance_id):
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=7)

    metrics = cloudwatch.get_metric_statistics(
        Namespace='AWS/EC2',
        MetricName='CPUUtilization',
        Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
        StartTime=start_time,
        EndTime=end_time,
        Period=3600,
        Statistics=['Average']
    )
    
    data_points = metrics['Datapoints']
    return sorted(data_points, key=lambda x: x['Timestamp'])

# Analyze metrics and make recommendations
def analyze_metrics(metrics):
    if not metrics:
        return "No data available"

    avg_cpu = sum([point['Average'] for point in metrics]) / len(metrics)

    if avg_cpu < 5:
        return "Terminate"
    elif avg_cpu > 80:
        return "Scale Up"
    else:
        return "No action required"

# Generate a CSV report
def generate_report(results):
    df = pd.DataFrame(results)
    df.to_csv('optimization_report.csv', index=False)
    print("Report saved as optimization_report.csv")

# Plot metrics for visualization
def plot_metrics(metrics, instance_id):
    if not metrics:
        print(f"No data for {instance_id}")
        return

    timestamps = [point['Timestamp'] for point in metrics]
    averages = [point['Average'] for point in metrics]

    plt.figure(figsize=(10, 6))
    plt.plot(timestamps, averages, marker='o', label='CPU Utilization (%)')
    plt.title(f"CPU Utilization for {instance_id}")
    plt.xlabel('Timestamp')
    plt.ylabel('CPU Utilization (%)')
    plt.legend()
    plt.grid()
    plt.show()

# Main function
def main():
    # Set up AWS services
    ec2, cloudwatch = setup_aws()

    # List EC2 instances
    instances = list_instances(ec2)
    print("EC2 Instances:", instances)

    results = []
    for instance in instances:
        if instance['State'] == 'running':
            metrics = get_cpu_utilization(cloudwatch, instance['InstanceId'])
            recommendation = analyze_metrics(metrics)
            results.append({
                'InstanceId': instance['InstanceId'],
                'Recommendation': recommendation
            })
            print(f"Instance {instance['InstanceId']} - {recommendation}")
            # Optional: Visualize metrics
            plot_metrics(metrics, instance['InstanceId'])

    # Generate a report
    generate_report(results)

if __name__ == "__main__":
    main()

