import boto3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configure AWS and email client
ec2 = boto3.resource('ec2')
ses = boto3.client('ses')  # If using AWS SES for email
sns = boto3.client('sns')  # If using SNS for notifications
region = "us-east-1"  # AWS Region
sender_email = "your-email@example.com"  # Email to send from
receiver_email = "itso-email@example.com"  # ITSO's email address
email_subject = "Warning: EC2 Instance Issue Detected"

# Function to send email
def send_email(subject, body):
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        # Use SES or SMTP to send email
        response = ses.send_email(
            Source=sender_email,
            Destination={'ToAddresses': [receiver_email]},
            Message={
                'Subject': {'Data': subject},
                'Body': {'Text': {'Data': body}},
            }
        )
        print("Email sent successfully.")
    except Exception as e:
        print(f"Error sending email: {str(e)}")

# Function to check mandatory tags
def check_mandatory_tags(instance):
    required_tags = ["Business Unit", "ITSO Email"]
    tags = {tag['Key']: tag['Value'] for tag in instance.tags or []}
    
    missing_tags = [tag for tag in required_tags if tag not in tags]
    
    return missing_tags

# Function to check security groups for open RDP
def check_open_rdp(instance):
    open_rdp_found = False
    for sg in instance.security_groups:
        if sg['GroupName'] == 'default':
            continue
        for permission in sg['IpPermissions']:
            if 'FromPort' in permission and permission['FromPort'] == 3389:
                for ip_range in permission.get('IpRanges', []):
                    if ip_range['CidrIp'] == '0.0.0.0/0':
                        open_rdp_found = True
                        break
    return open_rdp_found

# Function to check EC2 instance state
def check_instance_state(instance):
    if instance.state['Name'] == 'stopped':
        return True  # Instance is stopped
    return False

# Check all EC2 instances
def check_ec2_instances():
    for instance in ec2.instances.all():
        # Check for mandatory tags
        missing_tags = check_mandatory_tags(instance)
        if missing_tags:
            send_email(email_subject, f"Instance {instance.id} is missing the following mandatory tags: {', '.join(missing_tags)}")

        # Check if RDP is open to the internet
        if check_open_rdp(instance):
            send_email(email_subject, f"Instance {instance.id} has RDP (3389) open to the internet (0.0.0.0/0). Please investigate.")

        # Check if instance is stopped in production
        if check_instance_state(instance):
            send_email(email_subject, f"Instance {instance.id} in production has been stopped. Please investigate.")

# Lambda-like function to check EC2 instances periodically
def lambda_handler(event, context):
    check_ec2_instances()

if __name__ == "__main__":
    check_ec2_instances()
