# Samsara Marketplace Integration

## Overview

EDGE77 integrates with Samsara to provide AI-powered freight invoice auditing with real-time fleet data verification. This integration enables:

- **Invoice-to-Trip Matching**: Automatically match carrier invoices to actual trips in Samsara
- **Fuel Surcharge Verification**: Compare invoiced fuel charges against actual fuel data
- **Driver/Vehicle Validation**: Verify driver and vehicle information against Samsara records
- **Enhanced Audit Accuracy**: Use Samsara data to detect billing errors with higher confidence

## Setup Instructions

### For Samsara Partners

1. **Apply to Technology Partner Program**
   - Visit: https://developers.samsara.com/docs/technology-partner-program
   - Submit application with:
     - Company: Axal Global Inc.
     - Email: bainsarshveer1@gmail.com
     - Use Case: AI-powered freight invoice audit and dispute automation

2. **Get API Credentials**
   - After approval, you'll receive:
     - `SAMSARA_CLIENT_ID`
     - `SAMSARA_CLIENT_SECRET`
   - Set these in your environment or Secret Manager

3. **Configure Redirect URI**
   - Add to your Samsara app settings:
     ```
     https://edge77.app/v1/samsara/callback
     ```

### For Customers

1. **Connect Samsara Account**
   - Go to: https://edge77.app/dashboard
   - Click "Connect Samsara"
   - Authorize EDGE77 to access your fleet data

2. **What EDGE77 Accesses**
   - Vehicle information (ID, name, VIN)
   - Driver information (ID, name)
   - Trip history (routes, times, distances)
   - Fuel data (for surcharge verification)

3. **Data Usage**
   - EDGE77 uses this data to:
     - Match invoices to actual trips
     - Verify fuel surcharges
     - Validate driver/vehicle information
     - Improve audit accuracy

## API Endpoints

### Authentication
- `GET /v1/samsara/auth?client_id=xxx` - Initiate OAuth2 flow
- `GET /v1/samsara/callback` - Handle OAuth2 callback

### Data Access
- `GET /v1/samsara/status/{client_id}` - Check connection status
- `GET /v1/samsara/fleet/{client_id}` - Get fleet overview
- `GET /v1/samsara/vehicles/{client_id}` - List vehicles
- `GET /v1/samsara/drivers/{client_id}` - List drivers
- `GET /v1/samsara/trips/{client_id}` - Get trips

### Invoice Matching
- `GET /v1/samsara/match/{client_id}?vehicle_id=xxx&driver_name=xxx&trip_date=xxx` - Match invoice to Samsara data

## Database Schema

### samsara_credentials
- `client_id` - EDGE77 client ID
- `access_token` - Samsara OAuth access token
- `refresh_token` - Samsara OAuth refresh token
- `expires_at` - Token expiration timestamp
- `scope` - Granted permissions

### Enhanced freight_audits
- `samsara_vehicle_id` - Matched vehicle ID
- `samsara_driver_id` - Matched driver ID
- `samsara_trip_id` - Matched trip ID
- `samsara_match_data` - Full match details (JSON)

## Security

- Tokens encrypted at rest
- Refresh tokens used for long-term access
- Minimal scope requested (read-only)
- No write operations to Samsara

## Support

- **Technical**: bainsarshveer1@gmail.com
- **Company**: Axal Global Inc.
- **GitHub**: https://github.com/Bains1996/edge77
