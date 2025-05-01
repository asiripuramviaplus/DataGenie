import pyodbc
import json
import logging
from fastapi import FastAPI, Request
from db_connection import get_db_connection
from pydantic import BaseModel

class SQLAuditLogger:
    def __init__(self):
        from db_connection import get_db_connection
        self.conn = get_db_connection()

    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    def log_audit_record(self, audit_data: dict):
        ticket_number=None
        try:
            MAX_SQL_LENGTH = 4000
            MAX_JSON_LENGTH = 4000

            if isinstance(audit_data.get('IntentGeneratedData'), dict):
                audit_data['IntentGeneratedData'] = json.dumps(audit_data['IntentGeneratedData'], ensure_ascii=False)[:MAX_JSON_LENGTH]

            if 'QueryComplexity' in audit_data and isinstance(audit_data['QueryComplexity'], str):
                audit_data['QueryComplexity'] = audit_data['QueryComplexity'].replace("'", "''")[:MAX_JSON_LENGTH]

            if 'GeneratedSQL' in audit_data and isinstance(audit_data['GeneratedSQL'], str):
                audit_data['GeneratedSQL'] = audit_data['GeneratedSQL'].replace("'", "''")[:MAX_SQL_LENGTH]

            # print("\n[DEBUG] Audit Data:\n", json.dumps(audit_data, indent=4))
            cursor = self.conn.cursor()

            audit_id = audit_data.get('AuditId', 0)
            logging.info(f"$$$$$Audit ID Audit Logger-->: {audit_id}")

            # Step 1: Insert into DataGenieAudit and retrieve AuditId using OUTPUT param
            cursor.execute("""
            DECLARE @OutputAuditId INT = 0;
            EXEC [dbo].[sp_Insert_DataGenieAudit] 
                @Prompt=?,
                @GeneratedSQL=?,
                @Summary=?,
                @Recommendations=?,
                @GenerationTime=?,
                @QueryComplexity=?,
                @IsSQLGenerationSuccess=?,
                @IsIntentGenerated=?,
                @IntentGeneratedData=?,
                @IsReusedPrompt=?,
                @CreatedUser=?,
                @UpdatedUser=?,
                @AuditId=@OutputAuditId OUTPUT;
                SELECT @OutputAuditId AS AuditId;
            """, (
                audit_data.get('Prompt', ''),
                audit_data.get('GeneratedSQL', ''),
                audit_data.get('Summary', ''),
                audit_data.get('Recommendations', ''),
                audit_data.get('GenerationTime', 0),
                audit_data.get('QueryComplexity', ''),
                audit_data.get('IsSQLGenerationSuccess', 0),
                audit_data.get('IsIntentGenerated', 0),
                audit_data.get('IntentGeneratedData', ''),
                audit_data.get('IsReusedPrompt', 0),
                audit_data.get('CreatedUser', 'System'),
                audit_data.get('UpdatedUser', 'System'),
            ))

            # ✅ Required to move to the next result set (SELECT @OutputAuditId)
            cursor.nextset()

            audit_id_row = cursor.fetchone()
            audit_id = audit_id_row[0] if audit_id_row else None
            logging.info(f"***** Final Audit ID Used -->: {audit_id}")



            # Step 2: Log execution details to child table
            cursor.execute("""
                EXEC [dbo].[sp_Insert_DataGenieExecutionLog]
                    @AuditId=?,
                    @ExecutionTime=?,
                    @TotalRecords=?,
                    @Message=?,
                    @ExecutionResults=?,
                    @IsExecutionSuccess=?,
                    @ErrorMessage=?,
                    @ExecutedBy=?
            """, (
                audit_id,
                audit_data.get('ExecutionTime', 0),
                audit_data.get('TotalRecords', 0),
                audit_data.get('Message', ''),
                audit_data.get('ExecutionResults', ''),
                audit_data.get('IsExecutionSuccess', 0),
                audit_data.get('ErrorMessage', ''),
                audit_data.get('CreatedUser', 'SAaGpNGOaAtnPA')
            ))

            self.conn.commit()
            print("✅ Audit data and Execution log inserted successfully")

            # Check for failure and log ticket if needed
            self.logger.info(f"\nIsExecutionSuccess Value: {audit_data.get('IsExecutionSuccess', 0)}")
            if audit_data.get('IsExecutionSuccess', 0) == 0:
                self.logger.warning("\n❌ Execution failed. Triggering error email and ticket logging...\n")
                # Log Ticket and fetch Ticket Number
                ticket_number = self.log_ticket_and_get_ticket_number(
                    audit_id=audit_id,
                    execution_id=audit_id,
                    error_message=audit_data.get('ErrorMessage', 'Unknown error'),
                    stack_trace="No stack trace",
                    created_by="System")
                
                if ticket_number:
                    print(f"\n🎫 Ticket logged successfully. Ticket Number: {ticket_number}\n")
                    audit_data['TicketNumber'] = ticket_number  # Store if needed

                # Send error email
                from sendemail import send_error_email
                send_error_email(
                    ticket_number=ticket_number,
                    prompt=audit_data.get('Prompt', ''),
                    generated_sql=audit_data.get('GeneratedSQL', ''),
                    summary=audit_data.get('Summary', ''),
                    audit_id=audit_id,
                    error=audit_data.get('ErrorMessage', '')
                )
            return ticket_number

        except pyodbc.Error as e:
            error_message = str(e)
            audit_data['ErrorMessage'] = error_message  # Update ErrorMessage field
            self.map_error_message(audit_data, error_message)
            print(f"❌ Database Error during Audit Logging: {e}")
         
        except Exception as ex:
            print(f"❌ General Error during Audit Logging: {ex}")
            error_message = str(ex)
            audit_data['ErrorMessage'] = error_message  # Update ErrorMessage field
            self.map_error_message(audit_data, error_message)
        
    def map_error_message(self, audit_data: dict, error_message: str):
        try:
            # Extract error message
            error_message = error_message.split(']')[-1].strip()

            # Map the error message to the ErrorMessage field in audit_data
            audit_data['ErrorMessage'] = error_message
            logging.info(f"Mapped error message to audit_data: {error_message}")

        except Exception as e:
            logging.error(f"Failed to map error message to audit_data: {e}")

    def get_all_errors(self):
        """Fetch all stored error messages from the database."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT TicketNumber, ErrorMessage
                FROM dbo.DataGenieTicketLog
            """)
            
            errors = []
            for row in cursor.fetchall():
                errors.append({
                    "TicketNumber": row[0],
                    "ErrorMessage": row[1],
                })

            return {"status": "success", "errors": errors}
            
        except pyodbc.Error as e:
            self.logger.error(f"Error fetching error logs: {e}")
            return {"status": "error", "message": "Database error while fetching errors."}

        finally:
            cursor.close()
            
    def fetch_ticket_details(self):
        """Retrieve audit logs with prompts, SQL queries, intent data, execution success, errors, and ticket status."""
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        c.TicketNumber, 
                        a.Prompt, 
                        a.GeneratedSQL, 
                        a.IsIntentGenerated,
                        a.IntentGeneratedData,  
                        b.ErrorMessage,  
                        c.Status,
                        c.ResolvedBy -- Include ResolvedBy column
                    FROM 
                        dbo.DataGenieAudit AS a 
                    JOIN 
                        dbo.DataGenieExecutionLog AS b 
                        ON a.AuditId = b.AuditId 
                    JOIN 
                        dbo.DataGenieTicketLog AS c 
                        ON a.AuditId = c.AuditId;
                """)

                results = [
                    {
                        "TicketNumber": row[0],
                        "Prompt": row[1],
                        "GeneratedSQL": row[2],
                        "IsIntentGenerated": bool(row[3]),  # Convert to boolean
                        "IntentGeneratedData": row[4],
                        "ErrorMessage": row[5],
                        "TicketStatus": row[6],
                        "ResolvedBy": row[7]  # Add ResolvedBy to the result
                    }
                    for row in cursor.fetchall()
                ]

            return {"status": "success", "data": results}

        except Exception as e:
            return {"status": "error", "message": str(e)}

        finally:
            cursor.close()

            
    def log_ticket_and_get_ticket_number(self, audit_id, execution_id, error_message, stack_trace, created_by='System'):
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                DECLARE @TicketNumberOutput VARCHAR(50);
                EXEC [dbo].[sp_LogDataGenieTicket]
                    @AuditId=?,
                    @ExecutionId=?,
                    @ErrorMessage=?,
                    @StackTrace=?,
                    @CreatedUser=?;
            """, (audit_id, execution_id, error_message, stack_trace, created_by))
            
            ticket_row = cursor.fetchone()
            ticket_number = ticket_row[0] if ticket_row else None
            
            if ticket_number:
                print(f"🎫 Ticket logged successfully. Ticket Number: {ticket_number}")  # ✅ Print it here
            else:
                print("⚠️ No Ticket Number returned from procedure.")

            logging.info(f"🎫 Ticket Number Generated: {ticket_number}")
            self.conn.commit()
            return ticket_number
        

        except pyodbc.Error as e:
            print(f"❌ Database Error while logging ticket: {e}")
            return None
        except Exception as ex:
            print(f"❌ General Error while logging ticket: {ex}")
            return None

    def close(self):
        if self.conn:
            self.conn.close()
