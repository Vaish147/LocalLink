"""Seed 20 dummy shops into the locallink MySQL database."""
import mysql.connector
from werkzeug.security import generate_password_hash

MYSQL_CONFIG = {
    "host":     "localhost",
    "port":     3306,
    "user":     "locallink",          
    "password": "locallink123",       
    "database": "locallink",
    "charset":  "utf8mb4",
    "use_unicode": True,
}

PASSWORD = "shop123"

SHOPS = [
    # (name, owner, email, phone, category, website, gst, shop_act,
    #  open, close, address, city, state, pincode, description, tags,
    #  is_verified, is_active, rejection_reason)
    ("Spice Route Kitchen", "Rahul Deshmukh", "spiceroute@shop.in", "9876543210",
     "Restaurant", "https://spiceroute.in", "27AABCS1234A1Z5", "MH-SHOP-2023-001",
     "09:00", "23:00", "12 FC Road", "Pune", "Maharashtra", "411005",
     "Authentic Maharashtrian thali and street food served fresh daily.",
     "thali,biryani,pure-veg", 1, 1, None),

    ("Green Basket Grocery", "Priya Patil", "greenbasket@shop.in", "9823456789",
     "Grocery", "https://greenbasket.in", "27AABCG5678B1Z2", "MH-SHOP-2023-002",
     "07:00", "21:00", "5 Baner Road", "Pune", "Maharashtra", "411045",
     "Fresh vegetables, fruits, and daily essentials at fair prices.",
     "fresh,organic,vegetables", 1, 1, None),

    ("Urban Threads", "Amit Shah", "urbanthreads@shop.in", "9765432101",
     "Fashion", "https://urbanthreads.in", "27AABCU9012C1Z8", "MH-SHOP-2023-003",
     "10:00", "21:00", "Linking Road, Bandra West", "Mumbai", "Maharashtra", "400050",
     "Trendy clothing for men and women with the latest seasonal styles.",
     "clothing,ethnic,western", 1, 1, None),

    ("Gadget Hub Electronics", "Vikram Reddy", "gadgethub@shop.in", "9900112233",
     "Electronics", "https://gadgethub.co.in", "29AABCG3456D1Z1", "KA-SHOP-2023-004",
     "10:00", "20:00", "80 Feet Road, Koramangala", "Bangalore", "Karnataka", "560034",
     "Latest smartphones, accessories, and expert repairs under one roof.",
     "smartphones,accessories,repair", 1, 1, None),

    ("Glow Beauty Studio", "Sneha Joshi", "glowbeauty@shop.in", "9812345678",
     "Salon", "https://glowbeauty.in", "27AABCG7890E1Z9", "MH-SHOP-2023-005",
     "10:00", "20:00", "ITI Road, Aundh", "Pune", "Maharashtra", "411007",
     "Facials, skincare, and bridal makeovers by certified beauticians.",
     "facial,bridal,skincare", 1, 1, None),

    ("Blade & Fade Barbershop", "Karan Singh", "bladefade@shop.in", "9765432123",
     "Salon", None, "27AABCB2345F1Z3", "MH-SHOP-2024-011",
     "10:00", "22:00", "Veera Desai Road, Andheri West", "Mumbai", "Maharashtra", "400053",
     "Modern barbershop for men with beard styling and grooming services.",
     "haircut,beard,grooming", 0, 1, None),

    ("City Care Clinic", "Dr. Meera Iyer", "citycare@shop.in", "9823456700",
     "Healthcare", "https://citycareclinic.in", "27AABCC6789G1Z7", "MH-SHOP-2023-006",
     "09:00", "19:00", "6 Kalyani Nagar", "Pune", "Maharashtra", "411006",
     "General physicians, pediatric care, and lab diagnostics.",
     "doctor,diagnostics,pediatric", 1, 1, None),

    ("Bright Minds Academy", "Ravi Kumar", "brightminds@shop.in", "9871122334",
     "Education", "https://brightminds.edu", "07AABCB1234H1Z4", "DL-SHOP-2023-007",
     "08:00", "20:00", "Sector 3, Rohini", "Delhi", "Delhi", "110085",
     "Coaching for school students and competitive exams like JEE and NEET.",
     "coaching,jee,neet", 1, 1, None),

    ("FixIt Home Services", "Suresh Pawar", "fixit@shop.in", "9700123456",
     "Home Services", None, "27AABCF3456I1Z6", "MH-SHOP-2024-010",
     "08:00", "20:00", "Pimpri Chinchwad", "Pune", "Maharashtra", "411018",
     "Plumbing, electrical work, and appliance repairs at your doorstep.",
     "plumbing,electrical,repair", 0, 1, None),

    ("QuickRepair Electronics", "Mohammed Ali", "quickrepair@shop.in", "9711223344",
     "Repair", "https://quickrepair.in", "27AABCQ4567J1Z3", "MH-SHOP-2023-009",
     "10:00", "21:00", "Bandra East", "Mumbai", "Maharashtra", "400051",
     "Fast mobile and laptop repairs with genuine parts and warranty.",
     "mobile,laptop,repair", 1, 1, None),

    ("FitZone Gym", "Anjali Verma", "fitzone@shop.in", "9900887766",
     "Fitness", "https://fitzonegym.in", "29AABCF7890K1Z5", "KA-SHOP-2023-010",
     "06:00", "22:00", "Kharadi Main Road", "Bangalore", "Karnataka", "560036",
     "Modern gym with personal trainers, cardio, and strength training.",
     "gym,trainer,cardio", 1, 1, None),

    ("Cafe Mocha Lane", "Rohan Kapoor", "mochalane@shop.in", "9823012345",
     "Cafe", "https://mochalane.in", "27AABCM6789L1Z2", "MH-SHOP-2023-011",
     "08:00", "22:00", "Lane 7, Koregaon Park", "Pune", "Maharashtra", "411001",
     "Cozy cafe with artisanal coffee, pastries, and a relaxed vibe.",
     "coffee,cafe,bakery", 1, 1, None),

    ("Annapurna Bhojnalaya", "Lakshmi Nair", "annapurna@shop.in", "9823344556",
     "Restaurant", None, "27AABCA8901M1Z8", "MH-SHOP-2024-012",
     "11:00", "15:30", "Deccan Gymkhana", "Pune", "Maharashtra", "411004",
     "Home-style Maharashtrian and South Indian meals at budget prices.",
     "thali,home-style,south-indian", 0, 1, None),

    ("Saree Saga", "Kavita Agarwal", "sareesaga@shop.in", "9870011223",
     "Fashion", "https://sareesaga.in", "07AABCS2345N1Z1", "DL-SHOP-2024-005",
     "10:00", "21:00", "Chandni Chowk", "Delhi", "Delhi", "110006",
     "Traditional sarees, lehengas, and ethnic wear for all occasions.",
     "sarees,lehenga,ethnic", 0, 1, None),

    ("TechFix Laptop Care", "Arun Pillai", "techfix@shop.in", "9823456780",
     "Repair", None, "27AABCT5678O1Z7", "MH-SHOP-2023-015",
     "10:00", "20:00", "Magarpatta City", "Pune", "Maharashtra", "411013",
     "Laptop servicing, screen replacement, and data recovery.",
     "laptop,servicing,data-recovery", 0, 0,
     "Incomplete documentation and expired GST certificate."),

    ("MedPlus Pharmacy", "Deepak Sharma", "medplus@shop.in", "9820123456",
     "Pharmacy", "https://medplus.in", "27AABCM3456P1Z9", "MH-SHOP-2023-016",
     "00:00", "23:59", "Dadar West", "Mumbai", "Maharashtra", "400028",
     "24/7 pharmacy with prescription medicines and health essentials.",
     "pharmacy,medicines,24-7", 1, 1, None),

    ("Brew Haven Coffee", "Nisha Menon", "brewhaven@shop.in", "9900114477",
     "Cafe", "https://brewhaven.in", "29AABCB7890Q1Z6", "KA-SHOP-2023-013",
     "07:00", "23:00", "100 Feet Road, Indiranagar", "Bangalore", "Karnataka", "560038",
     "Specialty coffee house with single-origin beans and cold brews.",
     "specialty-coffee,cold-brew,beans", 1, 1, None),

    ("Yoga Bliss Studio", "Pooja Desai", "yogabliss@shop.in", "9823456799",
     "Fitness", None, "27AABCY9012R1Z4", "MH-SHOP-2024-014",
     "06:00", "20:00", "Viman Nagar", "Pune", "Maharashtra", "411014",
     "Hatha and vinyasa yoga classes for all levels, morning and evening.",
     "yoga,meditation,wellness", 0, 1, None),

    ("Fresh Fish Market", "Thomas Fernandes", "freshfish@shop.in", "9820889900",
     "Grocery", None, "27AABCF4567S1Z5", "MH-SHOP-2023-018",
     "06:00", "14:00", "Colaba Causeway", "Mumbai", "Maharashtra", "400005",
     "Daily fresh catch of fish and seafood sourced from local boats.",
     "fish,seafood,fresh", 1, 1, None),

    ("MovieMax Cinema", "Sanjay Gupta", "moviemax@shop.in", "9871234567",
     "Entertainment", "https://moviemax.in", "07AABCM6789T1Z3", "DL-SHOP-2024-003",
     "10:00", "23:30", "Saket District Centre", "Delhi", "Delhi", "110017",
     "Multi-screen cinema showing the latest Bollywood and Hollywood films.",
     "cinema,movies,entertainment", 0, 1, None),
]


def main():
    conn = mysql.connector.connect(**MYSQL_CONFIG)
    cur = conn.cursor()
    pw_hash = generate_password_hash(PASSWORD)

    inserted = skipped = 0
    for (shop_name, owner_name, email, phone, category, website, gst, shop_act,
         open_time, close_time, address, city, state, pincode, description,
         tags, is_verified, is_active, rejection_reason) in SHOPS:
        try:
            cur.execute("""
                INSERT INTO shops
                  (shop_name, owner_name, email, password_hash, phone, category,
                   website, gst, shop_act, owner_id_proof, logo, open_time, close_time,
                   address, city, state, pincode, description, tags,
                   is_verified, is_active, rejection_reason)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (shop_name, owner_name, email, pw_hash, phone, category,
                  website, gst, shop_act, "dummy_proof.pdf", None,
                  open_time, close_time, address, city, state, pincode,
                  description, tags, is_verified, is_active, rejection_reason))
            conn.commit()
            inserted += 1
        except mysql.connector.IntegrityError:
            skipped += 1

    cur.execute("SELECT COUNT(*) FROM shops");                   total    = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM shops WHERE is_verified=1"); verified = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM shops WHERE is_verified=0 AND is_active=1"); pending = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM shops WHERE is_active=0");  rejected = cur.fetchone()[0]
    cur.close(); conn.close()

    print(f"[OK] Inserted {inserted} shops (skipped {skipped} duplicates)")
    print(f"     Total:    {total}")
    print(f"     Verified: {verified}")
    print(f"     Pending:  {pending}")
    print(f"     Rejected: {rejected}")
    print(f"\n  Password for every dummy shop: {PASSWORD}")
    print(f"  Example login: spiceroute@shop.in / {PASSWORD}")


if __name__ == "__main__":
    main()