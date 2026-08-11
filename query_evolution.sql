-- Purge everything related to this instance from all tables
DELETE FROM "Session" WHERE "sessionId" IN (SELECT id FROM "Instance" WHERE name = 'travelinkeo');
DELETE FROM "Webhook" WHERE "instanceId" IN (SELECT id FROM "Instance" WHERE name = 'travelinkeo');
DELETE FROM "Setting" WHERE "instanceId" IN (SELECT id FROM "Instance" WHERE name = 'travelinkeo');
DELETE FROM "Instance" WHERE name = 'travelinkeo';

-- Verify
SELECT count(*) as sessions FROM "Session";
SELECT count(*) as instances FROM "Instance";
