#!/bin/bash


# Configuration: Set the threshold in days
INACTIVITY_THRESHOLD=60

# Get current date in Unix timestamp
CURRENT_DATE=$(date +%s)

# Function to deactivate user
deactivate_user() {
    local USERNAME=$1
    echo "Deactivating user: $USERNAME"

    # Deactivate the user's access keys
    aws iam list-access-keys --user-name "$USERNAME" --query 'AccessKeyMetadata[].AccessKeyId' --output text | tr '\t' '\n' | while read ACCESS_KEY; do
        aws iam update-access-key --user-name "$USERNAME" --access-key-id "$ACCESS_KEY" --status Inactive
    done

    # Disable the user's login profile if exists
    if aws iam get-user --user-name "$USERNAME" > /dev/null 2>&1; then
        aws iam delete-login-profile --user-name "$USERNAME" || echo "No login profile found for $USERNAME."
    fi

    echo "User $USERNAME deactivated."
}

# Get the list of IAM users
USER_LIST=$(aws iam list-users --query 'Users[].[UserName]' --output text)

# Iterate through each user and check their last activity
for USERNAME in $USER_LIST; do
    # Get the last activity timestamp of the user (via Get-User CLI)
    LAST_LOGIN=$(aws iam get-user --user-name "$USERNAME" --query 'User.PasswordLastUsed' --output text)

    # Check if the user has ever logged in
    if [ "$LAST_LOGIN" == "None" ]; then
        echo "User $USERNAME has never logged in, deactivating..."
        deactivate_user "$USERNAME"
    else
        # Convert the last login time to Unix timestamp
        LAST_LOGIN_TIMESTAMP=$(date -d "$LAST_LOGIN" +%s)

        # Calculate the difference in days
        DIFF_DAYS=$(( (CURRENT_DATE - LAST_LOGIN_TIMESTAMP) / 86400 ))

        if [ "$DIFF_DAYS" -ge "$INACTIVITY_THRESHOLD" ]; then
            echo "User $USERNAME has been inactive for $DIFF_DAYS days, deactivating..."
            deactivate_user "$USERNAME"
        else
            echo "User $USERNAME is active, skipping."
        fi
    fi
done
