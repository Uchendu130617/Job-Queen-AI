# JobQuick AI - Production Deployment Guide

## Pre-Deployment Checklist

### 1. Environment Configuration

```bash
# Copy template and configure
cp backend/.env.template backend/.env
```

**Critical configurations to change:**

- [ ] `JWT_SECRET`: Generate with `openssl rand -hex 32`
- [ ] `ADMIN_EMAIL`: Your admin email
- [ ] `ADMIN_PASSWORD`: Strong password (8+ chars, mixed case, numbers)
- [ ] `MONGO_URL`: Production MongoDB connection string
- [ ] `DB_NAME`: Production database name
- [ ] `CORS_ORIGINS`: Your production domain(s)
- [ ] `EMERGENT_LLM_KEY`: Your AI API key

### 2. Security Checklist

- [ ] All secrets are in .env (not hardcoded)
- [ ] JWT_SECRET is strong and random
- [ ] Admin password is changed from default
- [ ] CORS is configured for specific domains
- [ ] File upload limits are set appropriately
- [ ] Database has authentication enabled
- [ ] HTTPS is enabled on frontend

### 3. Database Setup

```bash
# The application creates indexes automatically on startup
# Verify MongoDB is accessible:
mongosh $MONGO_URL
```

**Recommended MongoDB setup:**
- Enable authentication
- Create dedicated database user with read/write permissions
- Configure backup strategy (daily recommended)
- Set up monitoring and alerts

### 4. Validate Configuration

```bash
cd /app/backend
python config.py
```

This will validate all environment variables and show warnings.

## Deployment Steps

### Option 1: Emergent Platform (Native)

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Production ready"
   git push origin main
   ```

2. **Configure Environment Variables**
   - Go to Emergent Dashboard
   - Add all .env variables in Settings > Environment Variables
   - Deploy from GitHub

3. **Verify Deployment**
   ```bash
   curl https://your-domain.com/health
   ```

### Option 2: Docker Deployment

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# Check health
curl http://localhost:8001/health
```

### Option 3: VPS/Cloud Deployment

1. **Install Dependencies**
   ```bash
   # Backend
   cd backend
   pip install -r requirements.txt
   
   # Frontend
   cd ../frontend
   yarn install
   yarn build
   ```

2. **Configure Nginx** (example)
   ```nginx
   server {
       listen 80;
       server_name yourdomain.com;
       
       location /api {
           proxy_pass http://localhost:8001;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
       
       location / {
           root /app/frontend/build;
           try_files $uri /index.html;
       }
   }
   ```

3. **Setup Process Manager** (PM2 or systemd)
   ```bash
   pm2 start "uvicorn server:app --host 0.0.0.0 --port 8001" --name jobquick-api
   pm2 save
   pm2 startup
   ```

## Post-Deployment

### 1. Verify Core Functions

```bash
# Health check
curl https://your-domain.com/health

# Test registration
curl -X POST https://your-domain.com/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123!","role":"job_seeker","full_name":"Test User"}'

# Test AI endpoint (requires token)
curl https://your-domain.com/api/health/detailed \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### 2. Admin Access

1. Login at `https://your-domain.com`
2. Use admin credentials from .env
3. Navigate to `/admin/dashboard`
4. Verify analytics are loading

### 3. Monitoring Setup

**Recommended monitoring:**
- Health endpoint: `/health` (check every 60s)
- Database connections
- API response times
- Error rates
- AI credit consumption

**Metrics to track:**
- User signups
- Job postings
- Applications submitted
- AI API calls
- Revenue (subscriptions + featured jobs)

### 4. Backup Strategy

```bash
# Daily MongoDB backup
mongodump --uri="$MONGO_URL" --out=/backups/$(date +%Y%m%d)

# Keep last 7 days
find /backups -type d -mtime +7 -exec rm -rf {} \;
```

## Scaling Considerations

### Horizontal Scaling
- Backend: Multiple instances behind load balancer
- MongoDB: Replica set for high availability
- File storage: Use S3/cloud storage instead of local

### Performance Optimization
- [ ] Enable Redis for session caching
- [ ] CDN for frontend assets
- [ ] Database query optimization (indexes created automatically)
- [ ] API response caching for public endpoints

## Rollback Plan

### Quick Rollback
```bash
# If using Emergent
# Use dashboard to rollback to previous deployment

# If using Docker
docker-compose down
git checkout <previous-commit>
docker-compose up -d

# If using PM2
pm2 stop jobquick-api
git checkout <previous-commit>
pm2 restart jobquick-api
```

### Database Rollback
```bash
# Restore from backup
mongorestore --uri="$MONGO_URL" /backups/20250128
```

## Troubleshooting

### Backend won't start
1. Check logs: `tail -f /var/log/supervisor/backend.err.log`
2. Verify environment: `python config.py`
3. Check database connection: `mongosh $MONGO_URL`

### 500 Errors
1. Check backend logs
2. Verify AI API key is valid
3. Check database indexes: See startup logs

### AI Features failing
1. Verify EMERGENT_LLM_KEY is set
2. Check user has AI credits
3. Check AI provider status

## Support

For deployment issues:
- Check logs first
- Review this guide
- Contact: support@emergent.sh (if using Emergent platform)
