"""
Helper to generate test files in real_test directory for end-to-end pipeline testing.
"""
import os

FILES = {
    # ── Rent Receipts (Jan to Jun) ──
    "rent_receipt_jan.txt": """RENT RECEIPT
Date: 05-Jan-2024
Receipt No: R-2024-001
Received with thanks from Mr. Karan Mehta the sum of Rupees Eight Thousand Five Hundred Only (Rs. 8,500) towards rent of Flat 402, Rajan Heights for the billing period of January 2024.
Paid to: Rajan Properties
Payment Mode: Bank Transfer""",

    "rent_receipt_feb.txt": """RENT RECEIPT
Date: 04-Feb-2024
Receipt No: R-2024-002
Received with thanks from Mr. Karan Mehta the sum of Rupees Eight Thousand Five Hundred Only (Rs. 8,500) towards rent of Flat 402, Rajan Heights for the billing period of February 2024.
Paid to: Rajan Properties
Payment Mode: Bank Transfer""",

    "rent_receipt_mar.txt": """RENT RECEIPT
Date: 05-Mar-2024
Receipt No: R-2024-003
Received with thanks from Mr. Karan Mehta the sum of Rs. 8,500 towards rent for the billing period of March 2024.
Paid to: Rajan Properties""",

    "rent_receipt_apr.txt": """RENT RECEIPT
Date: 04-Apr-2024
Receipt No: R-2024-004
Received with thanks from Mr. Karan Mehta the sum of Rs. 8,500 towards rent for the billing period of April 2024.
Paid to: Rajan Properties""",

    "rent_receipt_may.txt": """RENT RECEIPT
Date: 05-May-2024
Receipt No: R-2024-005
Received with thanks from Mr. Karan Mehta the sum of Rs. 8,500 towards rent for the billing period of May 2024.
Paid to: Rajan Properties""",

    "rent_receipt_jun.txt": """RENT RECEIPT
Date: 05-Jun-2024
Receipt No: R-2024-006
Received with thanks from Mr. Karan Mehta the sum of Rs. 8,500 towards rent for the billing period of June 2024.
Paid to: Rajan Properties""",

    # ── Electricity Bills (Mar to Jun) ──
    "electricity_bill_mar.txt": """BANGALORE ELECTRICITY SUPPLY COMPANY (BESCOM)
Consumer ID: 8749281-0
Bill Date: 15-Mar-2024
Billing Period: March 2024
Consumer Name: Karan Mehta
Amount Due: Rs. 1,240.00
Due Date: 28-Mar-2024
Payment Status: PAID""",

    "electricity_bill_apr.txt": """BANGALORE ELECTRICITY SUPPLY COMPANY (BESCOM)
Consumer ID: 8749281-0
Billing Period: April 2024
Consumer Name: Karan Mehta
Amount Due: Rs. 1,410.00
Payment Status: PAID""",

    "electricity_bill_may.txt": """BANGALORE ELECTRICITY SUPPLY COMPANY (BESCOM)
Consumer ID: 8749281-0
Billing Period: May 2024
Consumer Name: Karan Mehta
Amount Due: Rs. 1,550.00
Payment Status: PAID""",

    "electricity_bill_jun.txt": """BANGALORE ELECTRICITY SUPPLY COMPANY (BESCOM)
Consumer ID: 8749281-0
Billing Period: June 2024
Consumer Name: Karan Mehta
Amount Due: Rs. 1,890.00
Payment Status: PAID""",

    # ── EMI Receipts ──
    "emi_receipt_jan.txt": """HDFC BANK LOAN REPAYMENT RECEIPT
Loan Account Number: LN-9849201-B
Customer Name: Karan Mehta
Payment Date: 02-Jan-2024
Billing Period: January 2024
Repayment Amount: Rs. 12,450.00
Transaction Status: SUCCESS""",

    "emi_receipt_feb.txt": """HDFC BANK LOAN REPAYMENT RECEIPT
Loan Account Number: LN-9849201-B
Customer Name: Karan Mehta
Payment Date: 02-Feb-2024
Billing Period: February 2024
Repayment Amount: Rs. 12,450.00
Transaction Status: SUCCESS""",

    "emi_receipt_mar.txt": """HDFC BANK LOAN REPAYMENT RECEIPT
Loan Account Number: LN-9849201-B
Customer Name: Karan Mehta
Payment Date: 02-Mar-2024
Billing Period: March 2024
Repayment Amount: Rs. 12,450.00
Transaction Status: SUCCESS""",

    # ── CSV School Fees ──
    "school_fees.csv": """Date,Receipt Number,Student Name,Parent Name,Amount,Billing Period,School Name
2024-01-10,SCH-981,Aarav Mehta,Karan Mehta,3500,January 2024,Delhi Public School
2024-02-10,SCH-982,Aarav Mehta,Karan Mehta,3500,February 2024,Delhi Public School""",

    # ── Rejected Document ──
    "pizza_order.txt": """DOMINOS PIZZA ORDER INVOICE
Order No: 4829
Date: 12-May-2024
1x Large Pepperoni Pizza - Rs. 599
1x Garlic Bread - Rs. 149
Total: Rs. 748
Delivered to: Flat 402, Rajan Heights"""
}


def main():
    dest_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "real_test"))
    os.makedirs(dest_dir, exist_ok=True)
    print(f"Generating test files in: {dest_dir}...")
    for filename, content in FILES.items():
        filepath = os.path.join(dest_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  Created: {filename}")
    print("\nGeneration complete!")


if __name__ == "__main__":
    main()
