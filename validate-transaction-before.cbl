      >>SOURCE FORMAT FREE
      *>----------------------------------------------------------
      *> VALIDATE-TRANSACTION  (BEFORE-FIX VERSION)
      *>
      *> Business rule as originally written:
      *>   - REFUND transactions are allowed to carry a NEGATIVE
      *>     amount. This is a deliberate sign convention: the
      *>     downstream Salesforce integration (Refund_Amount__c)
      *>     uses a negative value to identify money going OUT
      *>     (a credit to the customer).
      *>   - All other transaction types must be positive.
      *>
      *> This is the "working" state of the system, before a
      *> developer makes the well-intentioned but breaking change
      *> in validate-transaction-after.cbl.
      *>----------------------------------------------------------
       IDENTIFICATION DIVISION.
       PROGRAM-ID. VALIDATE-TRANSACTION.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT TRANSACTION-FILE ASSIGN TO "transactions.dat"
               ORGANIZATION IS LINE SEQUENTIAL.
           SELECT OUTPUT-FILE ASSIGN TO "validated-output-before.dat"
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

           IF TRAN-TYPE = "REFUND    "
               MOVE "VALID" TO WS-STATUS
               MOVE "REFUND: NEGATIVE AMOUNT ALLOWED BY DESIGN"
                   TO WS-REASON
           ELSE
               IF TRAN-AMT < 0
                   MOVE "REJECTED" TO WS-STATUS
                   MOVE "NON-REFUND: NEGATIVE AMOUNT NOT ALLOWED"
                       TO WS-REASON
               ELSE
                   MOVE "VALID" TO WS-STATUS
                   MOVE "AMOUNT OK" TO WS-REASON
               END-IF
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
