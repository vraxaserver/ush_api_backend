The cleanest setup is:

* keep `authprofile` and `blogs` as separate backend services
* put each one behind its own load balancer target, or at least separate path targets
* create **one API Gateway HTTP API**
* route requests by path prefix:

  * `/api/v1/auth/*` and `/api/v1/profile/*` → `authprofile`
  * `/api/v1/blogs/*` → `blogs`

For most microservice cases, **API Gateway HTTP API** is the better starting point than the older REST API because it supports HTTP proxy integrations and private integrations through VPC links to ALB, NLB, or Cloud Map, with lower cost and simpler setup. ([AWS Documentation][1])

## Recommended architecture

If your services run inside AWS in a VPC:

`Client -> API Gateway HTTP API -> VPC Link -> ALB -> authprofile/blogs`

This is the usual pattern when DRF and FastAPI services are on ECS, EKS, EC2, or internal containers. API Gateway can use a **private integration** through a **VPC link**, and HTTP APIs support private integrations to **ALB, NLB, and Cloud Map**. ([AWS Documentation][2])

If your services are already publicly reachable, you can skip the VPC link and use **HTTP proxy integrations** directly to public service URLs. In that mode, API Gateway passes the full request and response through to the backend. ([AWS Documentation][3])

---

## Step by step

## 1) Decide your backend exposure model

Choose one of these:

### Option A — preferred: private backends

Use this when your DRF and FastAPI services are inside a VPC and should not be public.

* Put the services behind an **Application Load Balancer**
* Create listeners and target groups
* Use **API Gateway HTTP API + VPC Link** to reach the ALB privately ([AWS Documentation][2])

### Option B — simpler: public backends

Use this when each service already has a public HTTPS URL.

* Example:

  * `https://auth.internal-example.com`
  * `https://blogs.internal-example.com`
* Create HTTP proxy integrations from API Gateway straight to those URLs ([AWS Documentation][3])

---

## 2) Put each microservice behind a stable backend URL

You need a stable destination per service.

For example, with an ALB:

* `authprofile` service target:

  * `http://internal-alb/authprofile` or path-routed to a target group
* `blogs` service target:

  * `http://internal-alb/blogs`

A more practical pattern is to let the ALB do path routing too:

* `/api/v1/auth/*` → authprofile target group
* `/api/v1/profile/*` → authprofile target group
* `/api/v1/blogs/*` → blogs target group

API Gateway can then forward requests to one ALB listener, while ALB distributes to the correct service. API Gateway private integrations for HTTP APIs use the **listener ARN** of the load balancer when integrating via VPC link. ([AWS Documentation][4])

---

## 3) Create the load balancer

If using private integrations:

1. Create an **Application Load Balancer** in the same VPC as your services.
2. Create target groups:

   * `tg-authprofile`
   * `tg-blogs`
3. Register your DRF app instances/containers in `tg-authprofile`
4. Register your FastAPI app instances/containers in `tg-blogs`
5. Add ALB listener rules:

   * `/api/v1/auth/*` → `tg-authprofile`
   * `/api/v1/profile/*` → `tg-authprofile`
   * `/api/v1/blogs/*` → `tg-blogs`

Using an ALB is especially convenient for container-based microservices, and API Gateway VPC links support private integrations to ALB. ([AWS Documentation][2])

---

## 4) Create a VPC link in API Gateway

In API Gateway:

1. Open **API Gateway**
2. Create a new **VPC link**
3. Select the VPC, subnets, and security groups that can reach your ALB
4. Wait for the VPC link status to become **AVAILABLE**

AWS notes that VPC links create and manage ENIs in your account, and they can take a few minutes to become available. Also, if a VPC link gets no traffic for 60 days, it can become inactive. ([AWS Documentation][2])

---

## 5) Create an HTTP API in API Gateway

In API Gateway:

1. Choose **Create API**
2. Select **HTTP API**
3. Give it a name like `microservices-gateway`

HTTP APIs are the right fit here because you want mostly pass-through routing to existing HTTP services, not heavy request/response transformation. HTTP proxy integrations are designed for exactly this. ([AWS Documentation][3])

---

## 6) Create integrations

Now create integrations from API Gateway to your services.

### If using private integration through ALB

Create an integration that uses:

* integration type: **private / HTTP proxy**
* connection type: **VPC link**
* target: **ALB listener ARN**

For HTTP APIs, private integrations are created by first creating the VPC link and then creating an HTTP proxy integration that points at the ALB or NLB listener. ([AWS Documentation][4])

### If using public service URLs

Create HTTP proxy integrations such as:

* `authprofile-integration` → `https://auth.example.com`
* `blogs-integration` → `https://blogs.example.com`

HTTP proxy integration passes the full HTTP request and response through between API Gateway and the backend. ([AWS Documentation][3])

---

## 7) Create routes for each service path

Create these API Gateway routes:

For `authprofile`:

* `ANY /api/v1/auth/{proxy+}`
* `ANY /api/v1/profile/{proxy+}`

For `blogs`:

* `ANY /api/v1/blogs/{proxy+}`

This lets API Gateway forward all subpaths under those prefixes. API Gateway supports proxy-style routing patterns for this kind of setup. ([AWS Documentation][5])

In practice, your mappings become:

* `/api/v1/auth/login/` → authprofile
* `/api/v1/auth/logout/` → authprofile
* `/api/v1/auth/register/` → authprofile
* `/api/v1/profile/customers/` → authprofile
* `/api/v1/profile/employees/` → authprofile
* `/api/v1/blogs/` → blogs
* `/api/v1/blogs/{blog_id}/comments/` → blogs

---

## 8) Make sure the forwarded path matches what your apps expect

This is the most important implementation detail.

Your DRF and FastAPI apps already expect paths like:

* `/api/v1/auth/login/`
* `/api/v1/blogs/123/comments/`

So your integration should forward the path **unchanged**.

That means:

* do not strip `/api/v1`
* do not rewrite `/blogs` to `/`
* keep the route structure exactly as your services already use it

With HTTP proxy integrations, API Gateway is designed to pass through the request/response rather than forcing custom mapping logic. ([AWS Documentation][3])

---

## 9) Configure authorization

Decide where auth should happen.

You have two common choices:

### Choice 1 — let your services keep handling auth

This is easiest if DRF already issues/validates tokens and FastAPI already trusts those tokens.

API Gateway just forwards:

* `Authorization` header
* cookies
* request body

### Choice 2 — enforce auth in API Gateway too

You can add:

* JWT authorizers
* Lambda authorizers
* IAM auth, depending on your setup

API Gateway supports multiple authorization methods on private integrations too. ([AWS Documentation][4])

For your case, I would start with **Choice 1** unless you specifically want centralized gateway auth.

---

## 10) Enable CORS if your frontend calls the gateway directly

If a browser frontend calls API Gateway from another origin:

1. Enable CORS on the HTTP API
2. Allow methods you use: `GET, POST, PUT, PATCH, DELETE, OPTIONS`
3. Allow headers such as:

   * `Authorization`
   * `Content-Type`

Do this in API Gateway and also make sure your backend behavior is consistent.

---

## 11) Deploy a stage

Create a stage such as:

* `dev`
* `staging`
* `prod`

Then your API URL will look something like:

* `https://abc123.execute-api.region.amazonaws.com/prod/api/v1/auth/login/`

After that, test each route through API Gateway.

---

## 12) Add a custom domain

Once it works, create a custom domain such as:

* `api.yourdomain.com`

Then map your API stage to that domain. API Gateway supports custom domains and API mappings, including mapping stages to base paths on a single domain. HTTP and REST APIs can both be mapped to the same custom domain. ([AWS Documentation][6])

So you can expose:

* `https://api.yourdomain.com/api/v1/auth/login/`
* `https://api.yourdomain.com/api/v1/blogs/`

without showing the default AWS hostname.

---

## 13) Configure DNS

After creating the custom domain:

1. Request or import an ACM certificate
2. Attach it to the API Gateway custom domain
3. Create the DNS record in Route 53 or your DNS provider to point to the API Gateway domain target

AWS requires the DNS record so requests to your custom hostname actually reach API Gateway. HTTP API custom domains are Regional and support TLS 1.2. ([AWS Documentation][7])

---

## 14) Add logging and monitoring

Enable:

* API Gateway access logs
* CloudWatch metrics
* backend ALB logs if needed

Watch for:

* 4xx from gateway auth/routing problems
* 5xx from backend failures
* integration latency
* timeouts

Also remember that API Gateway does not retry backend timeouts for you; clients should handle retries where appropriate. ([AWS Documentation][8])

---

## Example route design

A simple production-friendly design:

* **One HTTP API**
* routes:

  * `ANY /api/v1/auth/{proxy+}` → authprofile integration
  * `ANY /api/v1/profile/{proxy+}` → authprofile integration
  * `ANY /api/v1/blogs/{proxy+}` → blogs integration
* custom domain:

  * `api.example.com`

That gives you a single public entry point while keeping the services separate behind the gateway.

---

## What to do in your backends

Usually, nothing major.

For DRF and FastAPI, just make sure:

* they trust forwarded headers if needed
* allowed hosts/origins include the API Gateway/custom domain
* generated absolute URLs use the correct host/proto if your app depends on them
* timeouts are reasonable
* health check endpoints exist for the load balancer

---

## Console-first checklist

If you want the shortest practical path:

1. Run both services inside one VPC
2. Put them behind one ALB with path-based rules
3. Create one API Gateway HTTP API
4. Create one VPC link to the ALB
5. Add routes:

   * `/api/v1/auth/{proxy+}`
   * `/api/v1/profile/{proxy+}`
   * `/api/v1/blogs/{proxy+}`
6. Attach each route to the right integration
7. Deploy `prod`
8. Test with the default execute-api URL
9. Add custom domain `api.yourdomain.com`
10. Switch client apps to the new domain

---

## Recommended final answer for your specific case

For your two microservices, I would implement it like this:

* **authprofile (DRF)** handles:

  * `/api/v1/auth/*`
  * `/api/v1/profile/*`
* **blogs (FastAPI)** handles:

  * `/api/v1/blogs/*`

Then expose them through **one AWS API Gateway HTTP API**, using **path-based routing** and either:

* **VPC link + ALB** if the services are private in AWS, or
* **HTTP proxy integrations** if the services already have public HTTPS endpoints. ([AWS Documentation][3])

If you want, I can turn this into a concrete AWS setup with:

* exact API Gateway route definitions
* ALB listener rule examples
* and a sample Terraform or CloudFormation template.

[1]: https://docs.aws.amazon.com/whitepapers/latest/best-practices-api-gateway-private-apis-integration/http-api.html?utm_source=chatgpt.com "HTTP API - Best Practices for Designing Amazon API Gateway Private APIs ..."
[2]: https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-vpc-links-v2.html?utm_source=chatgpt.com "Set up VPC links V2 in API Gateway - docs.aws.amazon.com"
[3]: https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-http.html?utm_source=chatgpt.com "Create HTTP proxy integrations for HTTP APIs - Amazon API Gateway"
[4]: https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-private.html?utm_source=chatgpt.com "Create private integrations for HTTP APIs in API Gateway"
[5]: https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-create-api-as-simple-proxy-for-http.html?utm_source=chatgpt.com "Tutorial: Create a REST API with an HTTP proxy integration"
[6]: https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-mappings.html?utm_source=chatgpt.com "Map API stages to a custom domain name for HTTP APIs"
[7]: https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-custom-domain-names.html?utm_source=chatgpt.com "Custom domain names for HTTP APIs in API Gateway"
[8]: https://docs.aws.amazon.com/apigateway/latest/developerguide/getting-started-aws-proxy.html?utm_source=chatgpt.com "Tutorial: Create a REST API with an AWS integration"
