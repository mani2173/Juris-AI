"""
Script to generate sample legal case PDFs for testing the Legal AI Simulator
"""
import os
from pathlib import Path

# Try using reportlab if available, otherwise create a simple text-based PDF structure
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    
    def create_legal_pdf():
        """Create a sample legal case PDF using reportlab"""
        
        # Create samples directory if it doesn't exist
        samples_dir = Path("data/sample_pdfs")
        samples_dir.mkdir(parents=True, exist_ok=True)
        
        # PDF 1: Criminal Case
        pdf_path_1 = samples_dir / "Sample_Criminal_Case.pdf"
        doc = SimpleDocTemplate(str(pdf_path_1), pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=12,
            alignment=1  # Center
        )
        
        story.append(Paragraph("STATE OF NEW YORK v. JAMES MILLER", title_style))
        story.append(Spacer(1, 0.3*inch))
        
        # Case Details
        story.append(Paragraph("<b>Case Number:</b> 2024-CV-1234", styles['Normal']))
        story.append(Paragraph("<b>Court:</b> New York Supreme Court", styles['Normal']))
        story.append(Paragraph("<b>Date:</b> February 15, 2024", styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        # Facts
        story.append(Paragraph("<b>FACTS:</b>", styles['Heading2']))
        facts = """
        The defendant, James Miller, is accused of theft of commercial property occurring on 
        January 10, 2024 at approximately 10:30 PM at the Manhattan Electronics Store located 
        at 450 Fifth Avenue, New York. The defendant allegedly entered the store and removed 
        four laptop computers valued at $4,500 each without paying. Security footage shows 
        a male matching the defendant's description entering the store and exiting with two 
        large bags containing electronic equipment.
        """
        story.append(Paragraph(facts, styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        # Charges
        story.append(Paragraph("<b>CHARGES:</b>", styles['Heading2']))
        story.append(Paragraph("1. Grand Larceny in the Fourth Degree (PL § 155.30)", styles['Normal']))
        story.append(Paragraph("2. Petit Larceny (PL § 155.25)", styles['Normal']))
        story.append(Paragraph("3. Possession of Stolen Property (PL § 165.40)", styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        # Arguments
        story.append(Paragraph("<b>PROSECUTION'S ARGUMENT:</b>", styles['Heading2']))
        prosecution = """
        The state contends that the defendant committed grand larceny by taking property 
        valued in excess of $1,000. The security footage clearly identifies the defendant. 
        Two of the four stolen laptops were recovered from the defendant's residence. 
        The defendant has two prior convictions for theft in 2019 and 2021, demonstrating 
        a pattern of criminal behavior. The evidence is overwhelming.
        """
        story.append(Paragraph(prosecution, styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        # Defense Arguments
        story.append(Paragraph("<b>DEFENSE'S ARGUMENT:</b>", styles['Heading2']))
        defense = """
        The defense argues that the identification is unclear due to poor quality security footage. 
        The defendant claims he purchased the laptops legitimately from another party and has 
        receipts. Furthermore, the defendant's prior convictions were for minor offenses over 
        five years ago and should not prejudice the jury. The prosecution has not established 
        mens rea beyond a reasonable doubt.
        """
        story.append(Paragraph(defense, styles['Normal']))
        
        doc.build(story)
        print(f"✅ Created {pdf_path_1}")
        
        # PDF 2: Constitutional Law Case
        pdf_path_2 = samples_dir / "Sample_Constitutional_Case.pdf"
        doc = SimpleDocTemplate(str(pdf_path_2), pagesize=letter)
        story = []
        
        story.append(Paragraph("CITIZENS FOR EQUAL PROTECTION v. STATE EDUCATION BOARD", title_style))
        story.append(Spacer(1, 0.3*inch))
        
        story.append(Paragraph("<b>Case Number:</b> 2024-CA-5678", styles['Normal']))
        story.append(Paragraph("<b>Court:</b> Federal District Court", styles['Normal']))
        story.append(Paragraph("<b>Date:</b> February 10, 2024", styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        story.append(Paragraph("<b>FACTS:</b>", styles['Heading2']))
        facts2 = """
        The State Education Board implemented a new admissions policy at public universities 
        that takes race into consideration as one factor among many. Student organizations 
        filed suit claiming this violates the Equal Protection Clause of the Fourteenth Amendment. 
        The plaintiffs argue that race-conscious admissions policies constitute illegal discrimination.
        """
        story.append(Paragraph(facts2, styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        story.append(Paragraph("<b>CONSTITUTIONAL ISSUES:</b>", styles['Heading2']))
        story.append(Paragraph("1. Equal Protection under the Fourteenth Amendment", styles['Normal']))
        story.append(Paragraph("2. Strict Scrutiny Standard for Race-Based Classifications", styles['Normal']))
        story.append(Paragraph("3. Compelling State Interest in Diversity", styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        story.append(Paragraph("<b>PLAINTIFFS' ARGUMENT:</b>", styles['Heading2']))
        plaintiffs = """
        The Equal Protection Clause prohibits all racial discrimination, whether benign or invidious. 
        The policy explicitly uses race in decision-making, which cannot survive strict scrutiny. 
        Historical precedent from Regents v. Bakke (1978) established that race cannot be the 
        sole determinant, and this policy crosses that line.
        """
        story.append(Paragraph(plaintiffs, styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        story.append(Paragraph("<b>DEFENDANTS' ARGUMENT:</b>", styles['Heading2']))
        defendants = """
        The policy uses race as a limited factor to achieve educational diversity, which serves 
        a compelling state interest. See Grutter v. Bollinger (2003). The policy does not establish 
        racial quotas nor does it exclude anyone based solely on race. The university maintains 
        holistic review of each application.
        """
        story.append(Paragraph(defendants, styles['Normal']))
        
        doc.build(story)
        print(f"✅ Created {pdf_path_2}")
        
        # PDF 3: Contract Law Case
        pdf_path_3 = samples_dir / "Sample_Contract_Case.pdf"
        doc = SimpleDocTemplate(str(pdf_path_3), pagesize=letter)
        story = []
        
        story.append(Paragraph("APEX TECHNOLOGIES INC. v. GLOBAL SOLUTIONS LLC", title_style))
        story.append(Spacer(1, 0.3*inch))
        
        story.append(Paragraph("<b>Case Number:</b> 2024-CC-9012", styles['Normal']))
        story.append(Paragraph("<b>Court:</b> State Court of Common Pleas", styles['Normal']))
        story.append(Paragraph("<b>Date:</b> February 12, 2024", styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        story.append(Paragraph("<b>FACTS:</b>", styles['Heading2']))
        facts3 = """
        Apex Technologies entered into a software development contract with Global Solutions LLC 
        dated January 1, 2023. The contract required delivery of custom software by December 31, 2023. 
        On October 15, 2023, Global Solutions informed Apex that a key engineer had left the company, 
        causing delays. The final delivery was made on January 15, 2024. Apex claims breach of contract 
        and seeks damages for late delivery. Global Solutions argues the delay was due to unforeseeable 
        circumstances (act of God clause) and requests enforcement of the contract as written.
        """
        story.append(Paragraph(facts3, styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        story.append(Paragraph("<b>KEY CONTRACT PROVISIONS:</b>", styles['Heading2']))
        story.append(Paragraph("Section 2.1: Delivery by December 31, 2023 (non-negotiable)", styles['Normal']))
        story.append(Paragraph("Section 5.3: Liquidated damages of $5,000 per week of delay", styles['Normal']))
        story.append(Paragraph("Section 8.2: Force Majeure clause applies only to natural disasters", styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        story.append(Paragraph("<b>PLAINTIFF'S ARGUMENT:</b>", styles['Heading2']))
        plaintiff_c = """
        A material breach occurred when delivery deadline was missed. The contract explicitly 
        states the deadline is non-negotiable. Employee departure does not qualify under the 
        force majeure clause which is limited to natural disasters. Apex relied on timely 
        delivery and suffered damages of $45,000 (9 weeks × $5,000).
        """
        story.append(Paragraph(plaintiff_c, styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        story.append(Paragraph("<b>DEFENDANT'S ARGUMENT:</b>", styles['Heading2']))
        defendant_c = """
        The loss of key personnel and the resulting reasonable delays do not constitute breach. 
        Global Solutions performed the work substantially as agreed and delivered a functioning 
        product. A 15-day delay in a year-long contract is de minimis. The employee departure 
        was unforeseeable and should be treated similarly to force majeure. Liquidated damages 
        should not apply to good faith delays.
        """
        story.append(Paragraph(defendant_c, styles['Normal']))
        
        doc.build(story)
        print(f"✅ Created {pdf_path_3}")
        
        print("\n✅ All sample PDFs created successfully in data/sample_pdfs/")
        
except ImportError:
    print("⚠️  reportlab not installed. Creating simple text-based samples instead...")
    
    # Fallback: Create text files that can be used as reference
    samples_dir = Path("data/sample_pdfs")
    samples_dir.mkdir(parents=True, exist_ok=True)
    
    # Create sample text file
    sample_content = """
LEGAL CASE SAMPLE - CRIMINAL LAW
Case: STATE OF NEW YORK v. JAMES MILLER
Case Number: 2024-CV-1234
Court: New York Supreme Court
Date: February 15, 2024

FACTS:
The defendant, James Miller, is accused of theft of commercial property occurring on 
January 10, 2024 at approximately 10:30 PM at the Manhattan Electronics Store located 
at 450 Fifth Avenue, New York. The defendant allegedly entered the store and removed 
four laptop computers valued at $4,500 each without paying. Security footage shows 
a male matching the defendant's description entering the store and exiting with two 
large bags containing electronic equipment.

CHARGES:
1. Grand Larceny in the Fourth Degree (PL § 155.30)
2. Petit Larceny (PL § 155.25)
3. Possession of Stolen Property (PL § 165.40)

PROSECUTION'S ARGUMENT:
The state contends that the defendant committed grand larceny by taking property valued 
in excess of $1,000. The security footage clearly identifies the defendant. Two of the four 
stolen laptops were recovered from the defendant's residence. The defendant has two prior 
convictions for theft in 2019 and 2021, demonstrating a pattern of criminal behavior. 
The evidence is overwhelming.

DEFENSE'S ARGUMENT:
The defense argues that the identification is unclear due to poor quality security footage. 
The defendant claims he purchased the laptops legitimately from another party and has receipts. 
Furthermore, the defendant's prior convictions were for minor offenses over five years ago 
and should not prejudice the jury. The prosecution has not established mens rea beyond 
a reasonable doubt.
    """
    
    with open(samples_dir / "Sample_Criminal_Case.txt", "w") as f:
        f.write(sample_content)
    
    print("✅ Created sample text files in data/sample_pdfs/")
    print("   Use these as reference or convert to PDF using services like:")
    print("   - LibreOffice Writer")
    print("   - Google Docs")
    print("   - Online converters (txt to PDF)")

if __name__ == "__main__":
    create_legal_pdf()
