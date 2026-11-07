# Tears down everything CloudScale created. Run only AFTER grading. Takes about 15-25 minutes
# (CloudFront and RDS deletions are slow). Does NOT touch the AWS Budget, billing settings or
# the cloudscale-deployer IAM user (see the manual steps printed at the end).
#
# Usage:  .\scripts\teardown.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$region = "us-east-1"

Write-Host "This will DESTROY the CloudScale stack in $region (VPC, RDS, S3 buckets and their contents, ALB, CloudFront, Lambda, SageMaker endpoint...)." -ForegroundColor Yellow
$answer = Read-Host "Type 'destroy' to continue"
if ($answer -ne "destroy") { Write-Host "Aborted."; exit 1 }

# 1. SageMaker objects are created by scripts, not Terraform: delete endpoint, configs, models.
Write-Host "`n[1/4] Deleting SageMaker endpoint, endpoint configs and models..."
python (Join-Path $root "ml\delete_endpoint.py")

# 2. Terraform-managed resources (buckets use force_destroy = true, so versioned objects go too).
Write-Host "`n[2/4] terraform destroy..."
Push-Location (Join-Path $root "infra")
try {
    terraform destroy -input=false -auto-approve
    if ($LASTEXITCODE -ne 0) { throw "terraform destroy failed" }
} finally { Pop-Location }

# 3. Log groups that AWS services created outside Terraform (SageMaker training/endpoint logs).
Write-Host "`n[3/4] Deleting SageMaker log groups..."
$groups = aws logs describe-log-groups --log-group-name-prefix "/aws/sagemaker/" --region $region --query "logGroups[].logGroupName" --output text
foreach ($g in ($groups -split "\s+" | Where-Object { $_ })) {
    aws logs delete-log-group --log-group-name $g --region $region
    Write-Host "  deleted $g"
}

# 4. Verify nothing billable is left.
Write-Host "`n[4/4] Verification (all should be empty / none):"
Write-Host "  EC2 instances:"; aws ec2 describe-instances --region $region --filters "Name=tag:Project,Values=CloudScale" "Name=instance-state-name,Values=pending,running,stopping,stopped" --query "Reservations[].Instances[].InstanceId" --output text
Write-Host "  RDS instances:"; aws rds describe-db-instances --region $region --query "DBInstances[?DBInstanceIdentifier=='cloudscale-db'].DBInstanceIdentifier" --output text
Write-Host "  Load balancers:"; aws elbv2 describe-load-balancers --region $region --query "LoadBalancers[?starts_with(LoadBalancerName,'cloudscale')].LoadBalancerName" --output text
Write-Host "  Elastic IPs:"; aws ec2 describe-addresses --region $region --query "Addresses[?Tags[?Key=='Project' && Value=='CloudScale']].PublicIp" --output text
Write-Host "  SageMaker endpoints:"; aws sagemaker list-endpoints --region $region --name-contains cloudscale --query "Endpoints[].EndpointName" --output text
Write-Host "  CloudFront distributions with comment 'CloudScale Lost & Found':"; aws cloudfront list-distributions --query "DistributionList.Items[?Comment=='CloudScale Lost & Found'].Id" --output text

Write-Host "`nDone. Manual steps left for you (the script deliberately does not do these):" -ForegroundColor Cyan
Write-Host "  1. Take the cleanup screenshot (docs\screenshots\cleanup-*.png): empty EC2, RDS, VPC and S3 consoles."
Write-Host "  2. Delete the access keys of the 'cloudscale-deployer' IAM user (and the user itself if you no longer need it)."
Write-Host "  3. Leave the 'Cloud Scale' Budget in place until grading is fully finished; check Billing -> Credits the next day."
Write-Host "  4. Delete the free domain record at your DNS provider if you created one."
