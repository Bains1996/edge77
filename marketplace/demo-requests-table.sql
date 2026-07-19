# demo_requests Table — Run in Supabase SQL Editor

Go to: https://supabase.com/dashboard/project/ruarvrwswjhtgywkkjie/sql/new

Paste and run:

```sql
CREATE TABLE IF NOT EXISTS demo_requests (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  full_name text NOT NULL,
  email text NOT NULL,
  company text NOT NULL,
  invoice_volume text,
  phone text,
  created_at timestamptz DEFAULT now()
);

-- Enable RLS
ALTER TABLE demo_requests ENABLE ROW LEVEL SECURITY;

-- Allow anonymous inserts (for the demo form)
CREATE POLICY "Allow anonymous inserts" ON demo_requests
  FOR INSERT WITH CHECK (true);

-- Allow authenticated reads
CREATE POLICY "Allow authenticated reads" ON demo_requests
  FOR SELECT USING (true);
```

## Verify Table Created

After running the SQL, test with:

```bash
curl -X POST "https://ruarvrwswjhtgywkkjie.supabase.co/rest/v1/demo_requests" \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -H "Prefer: return=minimal" \
  -d '{"full_name":"Test","email":"test@test.com","company":"Test Corp","invoice_volume":"1000"}'
```

Should return 201 Created.
