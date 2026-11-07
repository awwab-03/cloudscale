"""Generates docs/architecture.png (CloudScale architecture diagram) with Pillow.

Usage: python docs/make_architecture.py      (needs: pip install pillow)
"""
import math
import os

from PIL import Image, ImageDraw, ImageFont

W, H = 2400, 1640
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "architecture.png")

COMPUTE, STORAGE, DB, NET = "#D86613", "#3F8624", "#3B48CC", "#8C4FFF"
INTEG, SEC, ML, MGMT, USER = "#C7176E", "#B0084D", "#007F73", "#B0508D", "#445566"
INK, GREY, LINE = "#16191F", "#6B7480", "#33404F"


def font(size, bold=False):
    names = ["arialbd.ttf" if bold else "arial.ttf", "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"]
    for n in names:
        try:
            return ImageFont.truetype(n, size)
        except OSError:
            continue
    return ImageFont.load_default()


img = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(img)
F_TITLE, F_NODE, F_SUB, F_LBL, F_GRP, F_CIDR = (font(40, True), font(21, True), font(17), font(16, True),
                                                 font(20, True), font(16))


def wrap(text, fnt, width):
    lines = []
    for para in text.split("\n"):
        cur = ""
        for word in para.split():
            test = (cur + " " + word).strip()
            if fnt.getlength(test) <= width:
                cur = test
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


def group(x, y, w, h, label, color, cidr=None, right=False):
    d.rounded_rectangle([x, y, x + w, y + h], radius=14, outline=color, width=3)
    if right:
        d.text((x + w - 16 - F_GRP.getlength(label), y + 10), label, font=F_GRP, fill=color)
    else:
        d.text((x + 16, y + 10), label, font=F_GRP, fill=color)
    if cidr:
        d.text((x + w - 16 - F_CIDR.getlength(cidr), y + 13), cidr, font=F_CIDR, fill=GREY)


def node(x, y, w, h, title, sub, color):
    d.rounded_rectangle([x, y, x + w, y + h], radius=10, fill="white", outline=color, width=3)
    d.rounded_rectangle([x, y, x + w, y + 36], radius=10, fill=color)
    d.rectangle([x, y + 24, x + w, y + 36], fill=color)
    assert F_NODE.getlength(title) <= w - 20, f"title too long: {title}"
    d.text((x + 12, y + 7), title, font=F_NODE, fill="white")
    ty = y + 46
    for line in wrap(sub, F_SUB, w - 24):
        d.text((x + 12, ty), line, font=F_SUB, fill=INK)
        ty += 22
    assert ty - 6 <= y + h, f"text overflows node: {title}"


def label(text, cx, cy, color=LINE):
    wlen = F_LBL.getlength(text)
    d.rectangle([cx - wlen / 2 - 6, cy - 12, cx + wlen / 2 + 6, cy + 12], fill="white")
    d.text((cx - wlen / 2, cy - 9), text, font=F_LBL, fill=color)


def head(p, q, color):
    ang = math.atan2(p[1] - q[1], p[0] - q[0])
    s = 14
    d.polygon([p, (p[0] - s * math.cos(ang - 0.45), p[1] - s * math.sin(ang - 0.45)),
               (p[0] - s * math.cos(ang + 0.45), p[1] - s * math.sin(ang + 0.45))], fill=color)


def arrow(points, text=None, pos=None, color=LINE, start_head=False):
    for a, b in zip(points[:-1], points[1:]):
        d.line([a, b], fill=color, width=3)
    head(points[-1], points[-2], color)
    if start_head:
        head(points[0], points[1], color)
    if text:
        label(text, pos[0], pos[1], color)


d.text((40, 24), "CloudScale: Campus Lost & Found on AWS (us-east-1)", font=F_TITLE, fill=INK)
d.text((40, 76), "Flask + gunicorn on an Auto Scaling group behind ALB and CloudFront; async image pipeline; "
       "SageMaker + Bedrock AI helpers", font=F_SUB, fill=GREY)

# ---------------- edge / users ----------------
node(40, 640, 210, 100, "Students", "Browser, HTTPS", USER)
node(330, 620, 250, 140, "CloudFront", "HTTPS entry (*.cloudfront.net). Default: ALB, no cache. /media/*: S3 via OAC, cached", NET)
node(40, 300, 250, 120, "Route 53", "Hosted zone, A/AAAA alias to CloudFront (Plan B: queried via its own NS)", NET)

# ---------------- VPC ----------------
group(700, 120, 960, 890, "VPC", NET, cidr="10.20.0.0/16, us-east-1a + us-east-1b")
group(730, 165, 900, 195, "Public subnets", GREY, cidr="10.20.1.0/24, 10.20.2.0/24")
node(760, 205, 230, 135, "Load balancer (ALB)", "Listener :80. 403 unless X-Origin-Verify matches; SG only from CloudFront prefix list", NET)
node(1050, 205, 250, 135, "NAT instance", "t4g.micro, source/dest check off. Single NAT = known single point of failure", NET)
node(1380, 205, 220, 135, "Internet Gateway", "Public subnets and NAT egress", NET)

group(730, 380, 900, 245, "Private app subnets", GREY, cidr="10.20.11.0/24, 10.20.12.0/24")
node(760, 420, 360, 185, "EC2 Auto Scaling group", "min 2 / desired 2 / max 4, t3.micro AL2023, Flask + gunicorn :8000. "
                         "Target tracking: 50% avg CPU. No SSH (SSM only). Role: cloudscale-ec2-app", COMPUTE)
node(1330, 420, 270, 135, "S3 Gateway endpoint", "Free; private route tables reach S3 without the NAT", NET)

group(730, 650, 900, 190, "Private DB subnets", GREY, cidr="10.20.21.0/24, 10.20.22.0/24")
node(760, 690, 280, 135, "RDS PostgreSQL 16", "db.t4g.micro, single-AZ, 20 GB gp3, encrypted, not public. users / items / claims", DB)

# ---------------- AWS services (right) ----------------
sx, sw = 1790, 300
node(sx, 150, sw, 95, "Cognito user pool", "Sign up / sign in; ID token checked via JWKS", SEC)
node(sx, 265, sw, 95, "SageMaker endpoint", "cloudscale-category (serverless): TF-IDF + LogReg", ML)
node(sx, 380, sw, 95, "Bedrock (Nova Micro)", "Converse API: AI description writer", ML)
node(sx, 495, sw, 95, "SNS claim-notifications", "Email to owner, filter on owner_email", INTEG)
node(sx, 610, sw, 95, "Secrets Manager + SSM", "RDS password (managed), Flask key, stress flag", SEC)
node(2140, 495, 220, 95, "Owner's email", "Claim notification", USER)

# ---------------- monitoring ----------------
node(sx, 770, sw, 105, "CloudWatch", "Dashboard 'CloudScale' + 4 alarms (CPU, 5xx, Lambda errors, DLQ)", MGMT)
node(2140, 770, 220, 105, "SNS ops-alerts", "Email to i220971@nu.edu.pk", INTEG)

# ---------------- async pipeline ----------------
group(860, 1060, 1260, 330, "Async image pipeline", GREY, right=True)
node(890, 1105, 270, 135, "S3 uploads bucket", "originals/, thumbnails/, meta/. Private, versioned, lifecycle", STORAGE)
node(1260, 1105, 250, 135, "SQS image-jobs", "S3 event on originals/. Visibility 360 s", INTEG)
node(1610, 1105, 240, 135, "Lambda thumbnailer", "Pillow, 512 MB, outside the VPC", COMPUTE)
node(1950, 1105, 150, 135, "Rekognition", "Labels + moderation", ML)
node(1260, 1290, 250, 70, "SQS DLQ", "after 3 failed receives", INTEG)

# ---------------- ML / artifacts ----------------
group(860, 1425, 1260, 135, "Build and ML (one-off, run from the deployer's machine)", GREY, right=True)
node(890, 1465, 330, 80, "SageMaker training job", "ml.g5.xlarge, sklearn 1.2 container", ML)
node(1330, 1465, 380, 80, "S3 artifacts bucket", "app/ (zip), ml/ (code, data, model)", STORAGE)

# ---------------- arrows ----------------
arrow([(250, 690), (330, 690)])
arrow([(290, 360), (455, 360), (455, 620)], "alias A/AAAA", (455, 410))
arrow([(580, 650), (650, 650), (650, 272), (760, 272)])
label("HTTP :80", 590, 520)
label("+ X-Origin-Verify", 575, 546)
arrow([(975, 340), (975, 420)], "HTTP :8000", (1060, 402))
arrow([(985, 605), (985, 690)], "5432 TLS", (925, 640))
arrow([(1120, 450), (1280, 450), (1280, 340)], "egress", (1200, 434))
arrow([(1300, 272), (1380, 272)])
arrow([(1120, 530), (1330, 530)], "S3", (1225, 514))
# trunk to AWS APIs
d.line([(1120, 590), (1720, 590)], fill=LINE, width=3)
d.line([(1720, 197), (1720, 657)], fill=LINE, width=3)
for yy in (197, 312, 427, 542, 657):
    arrow([(1720, yy), (1790, yy)])
label("HTTPS API calls (via NAT)", 1400, 606)
arrow([(2090, 542), (2140, 542)])
arrow([(2090, 822), (2140, 822)])
# CloudFront -> S3 media
arrow([(450, 760), (450, 1172), (890, 1172)], "/media/* (OAC, cached thumbnails)", (640, 1150))
# EC2 -> S3 uploads (put originals)
arrow([(1070, 605), (1070, 1105)], "PutObject originals/", (1070, 930))
# S3 -> SQS -> Lambda -> Rekognition
arrow([(1160, 1172), (1260, 1172)], "event", (1210, 1152))
arrow([(1510, 1172), (1610, 1172)], "poll", (1560, 1152))
arrow([(1850, 1172), (1950, 1172)])
arrow([(1385, 1240), (1385, 1290)])
label("redrive", 1450, 1265)
arrow([(1730, 1240), (1730, 1372), (1030, 1372), (1030, 1240)], "writes thumbnails/ + meta/ JSON", (1380, 1372))
# build
arrow([(1220, 1505), (1330, 1505)], "model", (1275, 1485))

d.text((40, H - 44), "Tags: Project=CloudScale on every resource. Region us-east-1. No NAT Gateway, no Multi-AZ RDS, "
       "SageMaker endpoint is serverless. Source: infra/*.tf", font=F_SUB, fill=GREY)

img.save(OUT)
print("wrote", OUT)
