# Demo video script (target 7 minutes, limit 5-8)

Screen recording with voice-over. Have these tabs ready before recording: the site (CloudFront URL), AWS Console
(EC2 Auto Scaling group, target group, CloudWatch dashboard, SageMaker endpoint, S3 uploads bucket), a terminal in the repo,
and the inbox for the alert email. Blur or crop the account ID. Do not show keys or reveal any secret value.

| Time | Show | Say |
|---|---|---|
| 0:00 | Title slide or the architecture diagram | "CloudScale is a campus lost-and-found app on AWS: Flask on an Auto Scaling group behind an ALB and CloudFront, RDS, S3, an async image pipeline with SQS and Lambda, Cognito, SageMaker and Bedrock." |
| 0:40 | Site over HTTPS (CloudFront URL), browse the demo listings, use search and a filter | "Everything is served over HTTPS by CloudFront. The ALB only accepts traffic from CloudFront and only with a secret header." |
| 1:20 | Sign up with a real email, enter the Cognito code, sign in | "Authentication is Cognito: sign-up with an email code; the server verifies the ID token against the pool's keys." |
| 2:00 | Post a found item: type a short title and notes, click **Suggest category**, then **Write description with AI**, attach a photo, post | "Suggest category calls our own scikit-learn model on a serverless SageMaker endpoint. Write description calls Amazon Nova Micro on Bedrock. The photo goes straight to S3, never to the server's disk." |
| 3:00 | Refresh the item page: thumbnail and Rekognition tags appear. Show S3 `thumbnails/` and `meta/` objects, the SQS queue and the Lambda | "The upload triggered an S3 event into SQS, and a Lambda made the thumbnail and asked Rekognition for labels and a moderation check. The web request did not wait for any of that." |
| 3:40 | Second browser or account: claim the item; show the owner's email arriving | "Claiming publishes to SNS. Each user's email is subscribed with a filter on their address, so only the owner is emailed." |
| 4:20 | **Scaling scenario.** Dashboard open. In the terminal: turn the stress flag on, start `scripts/load_test.py`. Show CPU climbing, the alarm going to ALARM, the instance count going 2 to 3 or 4 (speed the clip up if needed). Show the alarm email | "Target tracking at 50% CPU scales the group out. The CPU alarm emails the ops-alerts topic. In our run throughput doubled and latency halved when we went from 2 to 4 instances, with zero failed requests." |
| 5:40 | **Failure scenario.** Keep the site open and refreshing. Terminate one instance in the console. Show the target group, the ASG activity and the replacement | "I'm terminating one app server. The ALB stops sending it traffic; there was a short blip of about 25 seconds in our test, then the site keeps serving from the other instance while the Auto Scaling group launches a replacement by itself." |
| 6:40 | Terminal: `nslookup app.cloudscale-lf.example <route53 name server>` | "Route 53 resolves the app record. We could not get a free delegated domain, so we show the zone through its own name servers; this is a known limitation." |
| 7:00 | Cost and IAM: Budget page and Cost Explorer; IAM role policy (scoped ARNs) | "A $100 AWS Budget with alerts is set up, and the cost stays at about $2-3 a day. No role has admin access." |
| 7:20 | Git history and `AI-DLC-LOG.md` | "Each phase was written as inception, construction with human review before any apply, and operations; the commit history and log show that process." |

## Before recording

1. Confirm the site works in the browser (sign up, post, photo, claim). If not, fix it first.
2. Put the stress flag back to `false` after the scaling clip.
3. Do the failure scenario with both instances healthy.
4. The scale-out takes about 7 to 8 minutes after the load starts and the CPU alarm needs two 5-minute periods (about 11 minutes in our run). Record the load test separately (about 14 minutes), then cut or speed up that clip to fit the video. Say in the voice-over that it is sped up.
