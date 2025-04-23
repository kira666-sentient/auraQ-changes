# AuraQ Deployment Guide

## Security Best Practices

### Environment Variables & Secrets

1. **JWT Secret Key**: 
   - NEVER commit your `.env` file with the real JWT secret key to Git.
   - For production, set the JWT_SECRET_KEY as an environment variable on your hosting platform.
   - Generate a new secure random key for production using:
     ```
     python -c "import secrets; print(secrets.token_hex(32))"
     ```

2. **Gemini API Key**:
   - Similar to JWT secrets, keep API keys out of your codebase.
   - Set these on your hosting platform (Vercel, Heroku, etc.) as environment variables.

3. **Environment Variables on Hosting Platforms**:
   - **Vercel**: Configure through the Vercel dashboard under Project Settings > Environment Variables
   - **Heroku**: Use `heroku config:set JWT_SECRET_KEY=your_secret_key`
   - **Railway/Render**: Configure in their respective dashboards

## Deployment Checklist

- [ ] Generate new JWT_SECRET_KEY for production
- [ ] Configure all environment variables on hosting platform
- [ ] Ensure `.env` is in `.gitignore`
- [ ] Set FLASK_ENV=production
- [ ] Configure FRONTEND_URL for CORS
- [ ] Test all authentication flows with the production configuration

## Database Considerations

For production deployment, consider:
- Using a managed database service instead of SQLite
- Configuring the DATABASE_URL environment variable
- Running migrations before deployment

## Security Headers

For additional security, configure your web server to add headers like:
- Content-Security-Policy
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- Strict-Transport-Security

## SSL/TLS

Always use HTTPS in production. Most hosting platforms handle this automatically.