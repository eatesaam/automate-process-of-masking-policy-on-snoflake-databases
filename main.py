import snowflake.connector

# snowflake account credentials details
ACCOUNT = ''
USER = ''
PASSWORD = ''

# create connection with snowflake and return connection
def get_connection():
    connection = snowflake.connector.connect(
        user=USER,
        password=PASSWORD,
        account=ACCOUNT
    )
    return connection


# get all databases from snowflake account and return these info
def get_databases(connection):
    cursor = connection.cursor()
    database_query = """
            SHOW DATABASES;
        """
    try:
        cursor.execute(database_query)
        databases = cursor.fetchall()
        print(databases)
        return databases
    finally:
        cursor.close()


# create dynamic data masking policy on snowflake
def create_masking_policy(connection, database, schema, data_type, role, policy_name):
    cursor = connection.cursor()
    masking_policy_query = """
            CREATE OR REPLACE MASKING POLICY {db}.{schema}.{policy}
            AS
            (val {dtype}) RETURNS {dtype} ->
            CASE
            WHEN current_role() in ('{role}')
            THEN '########'
            ELSE val
            END;
        """.format(db=database, schema=schema, dtype=data_type, role=role, policy=policy_name)
    try:
        cursor.execute(masking_policy_query)
        masking_policy = cursor.fetchall()
        print(masking_policy)
    finally:
        cursor.close()


# get db name, schema name, table name, and column name from snowflake account that consider to be PII data
def get_pii_columns(connection, database):
    cursor = connection.cursor()
    pii_col_query = """
            SELECT TABLE_CATALOG,TABLE_SCHEMA,TABLE_NAME, COLUMN_NAME, DATA_TYPE
            FROM {db}.INFORMATION_SCHEMA.COLUMNS
            WHERE COLUMN_NAME IN ('NAME','EMAIL','DOB','SSN','REGION','TELE','FAX','GENDER','PASSWORD','PHONE','CONTACT','ADDRESS','LOCATION','LATITUDE','LONGITUDE','GPS','POSTCODE','CITY','COUNTRY','COUNTY');
        """.format(db=database)
    try:
        cursor.execute(pii_col_query)
        all_pii_columns = cursor.fetchall()
        print(all_pii_columns)
        return all_pii_columns
    finally:
        cursor.close()


# apply dynamic data masking policy on scpefic columns that stored PII data
def apply_masking_policy(connection, db_name, schema_name, table_name, column_name, policy_name):
    cursor = connection.cursor()
    apply_masking_policy_query = """
            ALTER TABLE IF EXISTS {db}.{schema}.{table} MODIFY COLUMN {column}
            SET MASKING POLICY {db}.{schema}.{policy};
        """.format(db=db_name, schema=schema_name, table=table_name, column=column_name, policy=policy_name)
    try:
        cursor.execute(apply_masking_policy_query)
        apply_masking_policy = cursor.fetchall()
        print(apply_masking_policy)
    finally:
        cursor.close()


# get tables
def get_tables(connection, database, schema):
    cursor = connection.cursor()
    table_query = """
            SELECT TABLE_NAME
            FROM {db}.INFORMATION_SCHEMA.TABLES
            where TABLE_TYPE = 'BASE TABLE'
            AND TABLE_CATALOG = '{db}'
            AND TABLE_SCHEMA = '{schema}';
        """.format(db=database, schema=schema)
    try:
        cursor.execute(table_query)
        tables = cursor.fetchall()
        print(tables)
        return tables
    finally:
        cursor.close()


# main
def main():
    # get snowflake connection
    connection = get_connection()
    # get databases names
    databases_info = get_databases(connection)
    for database_info in databases_info:
        database = database_info[1]
        database = 'ADVANCE_CACHE_CLONE_DEV'
        schema = 'TRANSFORM'
        role = 'DATATEAM_ROLE'
        # get tables
        tables = get_tables(connection, database, schema)
        # get pii column names with table names from database
        pii_columns = get_pii_columns(connection, database)
        for pii_column in pii_columns:
                db_name = pii_column[0]
                schema_name = pii_column[1]
                table_name = pii_column[2]
                column_name = pii_column[3]
                data_type = pii_column[4]
                # check database name and schema name
                if schema_name == schema and db_name == database:
                    # check table type is table
                    if (table_name,) in tables:
                        print(pii_column)
                        print("check")
                        policy_name = db_name+'_'+schema_name+'_'+column_name + \
                            '_'+data_type+'_pii_masking_policy_'+role+'_role'
                        # create masking policy
                        create_masking_policy(
                            connection, database, schema, data_type, role, policy_name)
                        # apply masking policy on specific columns of table in database
                        apply_masking_policy(
                            connection, db_name, schema_name, table_name, column_name, policy_name)
        # close connection
        connection.close()
        print("Policy Applied")


# run main
if __name__ == '__main__':
    main()
