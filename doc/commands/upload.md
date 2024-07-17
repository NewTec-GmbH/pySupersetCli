# Upload

Upload a JSON file to a Superset instance.

The user mus supply the following parameters:

- database: DB to upload the data to.
- table: Existing table in the database to save the data to.
- file: JSON-formatted file containing the data.

```cmd
pySupersetCli -u <user> -p <password> -s <server_url> --basic_auth --no_ssl upload --database "TEST" --table "dummy" --file "input.json"
```

## JSON File format

The JSON file must contain a JSON Object, in which the keys are interpreted as the columns of the table. Nested objects are not accepted and the command will fail in case a nested object is supplied. Each time the command is called, a new row will be appended to the database/table specified.

If the table already exists, it is not possible to change the column names/order (no changes in the schema allowed).
