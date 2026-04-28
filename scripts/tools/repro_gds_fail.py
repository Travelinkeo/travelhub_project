import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings')
django.setup()

from core.services.ai_engine import ai_engine

raw_text = """SXFSIE
 1.1CASTANO VALENCIA/JOHN JAIRO*AW918782
 2.1NINO CORZO/ANNY ZULAY*AX026962
 1 TK 224S 12APR 7 CCSIST*HK2  0030  1910  /DCTK*SII3YM /E
 2 TK  26S 13APR 1 ISTPVG*HK2  0130  1645  /DCTK*SII3YM /E
 3 TK  27A 27APR 1 PVGIST*HK2  2225  0525   28APR 2
                                               /DCTK*SII3YM /E
 4 TK 223A 28APR 2 ISTCCS*HK2  1700  2240  /DCTK*SII3YM /E
TKT/TIME LIMIT
*PQ
                 PRICE QUOTE RECORD - DETAILS                  
                                                               
FARE NOT GUARANTEED UNTIL TICKETED                            
                                                               
PQ 1  NCB                                                      
                                                               
BASE FARE                     TAXES/FEES/CHARGES           TOTAL
USD2741.00                       1119.30XT          USD3860.30ADT
XT BREAKDOWN                                                  
        28.00YQ        740.00YR         72.90AK          2.50C2
       219.30YN         27.40EU         11.60TR         13.00CN
         4.60M6                                                
ADT-01  SV3XEX AV3XEX                                          
CCS TK X/IST TK SHA1134.50TK X/IST TK CCS1606.00NUC2740.50END R
OE1.00
VALIDATING CARRIER - TK                                        
NONEND/TK ONLY                                                
01 O CCS TK 224S 12APR 0030  SV3XEX          12APR2612APR26 02P
02 X IST TK  26S 13APR  130  SV3XEX          13APR2613APR26 02P
03 O PVG TK  27A 27APR 2225  AV3XEX          27APR2627APR26 02P
04 X IST TK 223A 28APR 1700  AV3XEX          28APR2628APR26 02P
     CCS                                                      
FARE SOURCE - ATPC                                            
2JSI 2JSI *AR8 1611/11MAR26                          PRICE-SYSTEM
"""

print("Starting GDS Analysis...")
result = ai_engine.analyze_gds_terminal(raw_text)

print("\n--- RESULT ---")
print(json.dumps(result, indent=2))

if "error" in result:
    print(f"\nFAILURE DETECTED: {result['error']}")
else:
    print("\nSUCCESS!")
