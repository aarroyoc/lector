provider "aws" {
  region  = "eu-west-3"
  version = "2.60.0"
}

resource "aws_s3_bucket" "lector-www" {
    bucket = "lector.adrianistan.eu"
    acl = "public-read"

    website {
        index_document = "index.html"
    }
}

output "website_cname" {
    value = aws_s3_bucket.lector-www.website_endpoint
}

resource "aws_lambda_function" "lector" {
    filename = "function.zip"
    function_name = "lector"
    role = aws_iam_role.lector.arn
    handler = "main.handler"

    source_code_hash = filebase64sha256("function.zip")
    runtime = "python3.8"

    memory_size = 256
    timeout = 900
}

resource "aws_iam_role" "lector" {
  name = "lector"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

resource "aws_iam_policy" "lector" {
  name = "lector"
  policy = file("policy.json")
}

resource "aws_iam_role_policy_attachment" "lector" {
  role       = aws_iam_role.lector.name
  policy_arn = aws_iam_policy.lector.arn
}

resource "aws_cloudwatch_event_rule" "lector-daily" {
    name = "lector-daily"
    description = "Run Lector Lambda every day"

    schedule_expression = "rate(24 hours)"
}

resource "aws_cloudwatch_event_target" "lector-daily" {
    rule = aws_cloudwatch_event_rule.lector-daily.name
    target_id = "lector-daily"
    arn = aws_lambda_function.lector.arn
}