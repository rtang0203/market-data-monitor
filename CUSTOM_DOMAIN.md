# Custom Domain Setup Guide

This guide explains how to set up a custom domain for your dashboard instead of using the IP address.

## Overview

Currently accessing dashboard at: `http://138.197.119.94:8080`
Goal: Access dashboard at: `https://dashboard.yourdomain.com`

---

## Option 1: Simple DNS Setup (Keep Port 8080)

### Pros & Cons

✅ **Pros:**
- Quick and easy (5 minutes)
- No additional software needed

❌ **Cons:**
- Users still need to type `:8080` in URL
- No HTTPS/SSL (not secure)

### Steps

1. **Register a domain** (if you don't have one):
   - Providers: Namecheap, Google Domains, Cloudflare, Porkbun
   - Cost: ~$10-15/year

2. **Add DNS A Record:**
   - Go to your domain registrar's DNS settings
   - Add new **A Record**:
     - **Name/Host**: `dashboard` (or `@` for root domain)
     - **Value/Points to**: `138.197.119.94` (your droplet IP)
     - **TTL**: `300` (5 minutes)
   - Save changes

3. **Wait for DNS propagation** (5-30 minutes)

4. **Access your dashboard:**
   - `http://dashboard.yourdomain.com:8080`

---

## Option 2: Professional Setup (Nginx + HTTPS) ⭐ Recommended

### Pros & Cons

✅ **Pros:**
- Clean URL (no port number needed)
- HTTPS/SSL encryption (secure)
- Standard web ports (80/443)
- Professional appearance

❌ **Cons:**
- Slightly more complex setup (15-20 minutes)
- Requires Nginx installation

### Prerequisites

- Custom domain registered and DNS A record configured (see Option 1, step 2)
- SSH access to your DigitalOcean droplet

---

## Step-by-Step: Nginx + HTTPS Setup

### Step 1: Point Your Domain (DNS Configuration)

**On your domain registrar's website:**

1. Go to DNS management
2. Add **A Record**:
   ```
   Name:   dashboard
   Type:   A
   Value:  138.197.119.94
   TTL:    300
   ```
3. Save and wait 5-30 minutes for propagation

**Check DNS propagation:**
```bash
# From your local machine
dig dashboard.yourdomain.com

# Should show your droplet IP
```

---

### Step 2: Install Nginx and Certbot

**SSH into your droplet:**

```bash
ssh root@138.197.119.94
cd market-data-monitor
```

**Install required packages:**

```bash
# Update package list
apt-get update

# Install Nginx (web server / reverse proxy)
apt-get install -y nginx

# Install Certbot (for free SSL certificates)
apt-get install -y certbot python3-certbot-nginx

# Verify installation
nginx -v
certbot --version
```

---

### Step 3: Configure Nginx

**Create Nginx configuration file:**

```bash
nano /etc/nginx/sites-available/dashboard
```

**Paste this configuration:**

```nginx
server {
    listen 80;
    server_name dashboard.yourdomain.com;

    # Redirect HTTP to HTTPS (will be added by certbot)

    location / {
        # Proxy requests to your dashboard container
        proxy_pass http://localhost:8080;

        # Pass headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (if needed in future)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

**Important:** Replace `dashboard.yourdomain.com` with your actual domain!

**Save and exit:** `Ctrl+X`, then `Y`, then `Enter`

---

### Step 4: Enable the Site

```bash
# Create symbolic link to enable the site
ln -s /etc/nginx/sites-available/dashboard /etc/nginx/sites-enabled/

# Test Nginx configuration
nginx -t

# Should output:
# nginx: configuration file /etc/nginx/nginx.conf test is successful

# Restart Nginx
systemctl restart nginx

# Check Nginx status
systemctl status nginx
```

---

### Step 5: Configure Firewall

```bash
# Allow Nginx through firewall (ports 80 and 443)
ufw allow 'Nginx Full'

# Check firewall status
ufw status
```

You should see:
```
80/tcp       ALLOW       Nginx Full
443/tcp      ALLOW       Nginx Full
8080/tcp     ALLOW       Anywhere
```

---

### Step 6: Add HTTPS/SSL Certificate (Let's Encrypt)

**Run Certbot to get free SSL certificate:**

```bash
certbot --nginx -d dashboard.yourdomain.com
```

**Answer the prompts:**
1. Enter email address (for renewal notifications)
2. Agree to terms of service: `Y`
3. Share email with EFF (optional): `Y` or `N`
4. Redirect HTTP to HTTPS: `2` (recommended)

**Certbot will:**
- ✅ Obtain SSL certificate from Let's Encrypt
- ✅ Automatically configure Nginx for HTTPS
- ✅ Set up automatic renewal (certificates last 90 days)

**Test auto-renewal:**
```bash
certbot renew --dry-run
```

---

### Step 7: Verify Everything Works

**Check your dashboard:**

1. **HTTP (should redirect to HTTPS):**
   ```
   http://dashboard.yourdomain.com
   ```

2. **HTTPS (should work):**
   ```
   https://dashboard.yourdomain.com
   ```

3. **Old IP + port (should still work):**
   ```
   http://138.197.119.94:8080
   ```

**Check SSL certificate:**
- Click the padlock icon in browser
- Should show "Connection is secure"
- Certificate issued by "Let's Encrypt"

---

## Troubleshooting

### DNS not resolving

```bash
# Check DNS from droplet
dig dashboard.yourdomain.com

# Should show your droplet IP in the ANSWER SECTION
```

If not showing, wait longer or check DNS configuration at your registrar.

### Nginx errors

```bash
# Check Nginx logs
tail -n 50 /var/log/nginx/error.log

# Test Nginx config
nginx -t

# Restart Nginx
systemctl restart nginx
```

### SSL certificate issues

```bash
# Check certificate status
certbot certificates

# Manually renew if needed
certbot renew

# Check Nginx config was updated
cat /etc/nginx/sites-available/dashboard
```

### Dashboard not loading

```bash
# Check if dashboard container is running
docker-compose ps

# Check dashboard logs
docker-compose logs dashboard

# Test dashboard directly on port 8080
curl http://localhost:8080/api/funding-rates
```

### Firewall blocking traffic

```bash
# Check firewall status
ufw status

# Allow Nginx if not already allowed
ufw allow 'Nginx Full'

# Check if port 8080 is open locally
netstat -tlnp | grep 8080
```

---

## Maintenance

### SSL Certificate Renewal

Certbot automatically renews certificates. Check auto-renewal:

```bash
# Test renewal process
certbot renew --dry-run

# Check certificate expiry
certbot certificates
```

Certificates auto-renew ~30 days before expiration.

### Nginx Configuration Changes

After editing Nginx config:

```bash
# Test configuration
nginx -t

# Reload Nginx (no downtime)
systemctl reload nginx

# Or restart Nginx
systemctl restart nginx
```

---

## Using Subdomain vs Root Domain

### Subdomain (Recommended)
- URL: `https://dashboard.yourdomain.com`
- DNS: A record with name `dashboard`
- Can use main domain for other purposes

### Root Domain
- URL: `https://yourdomain.com`
- DNS: A record with name `@` or leave blank
- Use entire domain for dashboard

Replace `dashboard.yourdomain.com` with `yourdomain.com` in all configs if using root domain.

---

## Optional: Add Basic Authentication

To password-protect your dashboard:

```bash
# Install apache2-utils for htpasswd
apt-get install -y apache2-utils

# Create password file (replace 'username' with your username)
htpasswd -c /etc/nginx/.htpasswd username

# Enter password when prompted

# Edit Nginx config
nano /etc/nginx/sites-available/dashboard
```

Add inside the `location /` block:

```nginx
location / {
    auth_basic "Dashboard Login";
    auth_basic_user_file /etc/nginx/.htpasswd;

    proxy_pass http://localhost:8080;
    # ... rest of config
}
```

Then reload Nginx:
```bash
nginx -t
systemctl reload nginx
```

---

## Cost Summary

- **Domain registration**: $10-15/year
- **SSL certificate**: FREE (Let's Encrypt)
- **Nginx**: FREE (open source)
- **Total**: ~$10-15/year for domain only

---

## Quick Reference

```bash
# View Nginx config
cat /etc/nginx/sites-available/dashboard

# Edit Nginx config
nano /etc/nginx/sites-available/dashboard

# Test Nginx config
nginx -t

# Reload Nginx
systemctl reload nginx

# View SSL certificates
certbot certificates

# Renew SSL certificates (automatic, but manual trigger)
certbot renew

# Check Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# Check dashboard container
docker-compose ps
docker-compose logs -f dashboard
```
