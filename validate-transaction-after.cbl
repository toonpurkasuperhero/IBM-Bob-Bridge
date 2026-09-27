      >>SOURCE FORMAT FREE
      *>----------------------------------------------------------
      *> VALIDATE-TRANSACTION  (AFTER-FIX VERSION)
      *>
      *> A developer notices negative amounts in the transaction
      *> file and assumes it's a data-entry bug. They "fix" it by
      *> rejecting ALL negative amounts, regardless of type.
      *>
      *> This looks like a safe, obvious improvement in isolation.
      *> It silently breaks the REFUND flow, because the downstream
      *> Salesforce integration relies on the negative sign to
      *> identify a credit (see integration_mapping.json).
      *>
      *> THIS IS THE CHANGE BOB BRIDGE SHOULD CATCH.
      *> See the-fix.diff for the exact one-rule change that
      *> caused this.
      *>----------------------------------------------------------
       IDENTIFICATION DIVISION.
       PROGRAM-ID. VALIDATE-TRANSACTION.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT TRANSACTION-FILE ASSIGN TO "transactions.dat"
               ORGANIZATION IS LINE SEQUENTIAL.
           SELECT OUTPUT-FILE ASSIGN TO "validated-output-after.dat"
               ORGANIZATION IS LINE SEQUENTIAL.

       DATA DIVISION.
       FILE SECTION.
       FD  TRANSACTION-FILE.
       01  TRAN-RECORD.
           05  TRAN-ID         PIC X(6).
           05  TRAN-TYPE       PIC X(10).
           05  TRAN-AMT        PIC S9(6)V99 SIGN LEADING SEPARATE.

       FD  OUTPUT-FILE.
       01  OUT-LINE            PIC X(70).

       WORKING-STORAGE SECTION.
       01  WS-EOF              PIC X VALUE "N".
       01  WS-STATUS           PIC X(8).
       01  WS-REASON           PIC X(40).
       01  WS-AMT-DISPLAY      PIC -(6)9.99.

       PROCEDURE DIVISION.
       MAIN-LOGIC.
           OPEN INPUT TRANSACTION-FILE
           OPEN OUTPUT OUTPUT-FILE

           PERFORM UNTIL WS-EOF = "Y"
               READ TRANSACTION-FILE
                   AT END MOVE "Y" TO WS-EOF
                   NOT AT END PERFORM VALIDATE-RECORD
               END-READ
           END-PERFORM

           CLOSE TRANSACTION-FILE
           CLOSE OUTPUT-FILE
           STOP RUN.

       VALIDATE-RECORD.
           MOVE TRAN-AMT TO WS-AMT-DISPLAY

           IF TRAN-AMT < 0
               MOVE "REJECTED" TO WS-STATUS
               MOVE "NEGATIVE AMOUNT NOT ALLOWED (NEW RULE)"
                   TO WS-REASON
           ELSE
               MOVE "VALID" TO WS-STATUS
               MOVE "AMOUNT OK" TO WS-REASON
           END-IF

           STRING TRAN-ID      DELIMITED BY SIZE
                  "|"          DELIMITED BY SIZE
                  TRAN-TYPE    DELIMITED BY SIZE
                  "|"          DELIMITED BY SIZE
                  WS-AMT-DISPLAY DELIMITED BY SIZE
                  "|"          DELIMITED BY SIZE
                  WS-STATUS    DELIMITED BY SIZE
                  "|"          DELIMITED BY SIZE
                  WS-REASON    DELIMITED BY SIZE
                  INTO OUT-LINE
           END-STRING

           WRITE OUT-LINE
           .
