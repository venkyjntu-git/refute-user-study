"""
Code-mixed versions of the study specifications (see seed_study.py).

DRAFTS — every text here must be checked by a native speaker against the
English version before the pilot: an ambiguity introduced in translation
produces disputed counter-examples.

Conventions used throughout, so the versions stay comparable:
- Technical terms (function, list, integer, return, position, consecutive,
  absolute difference, ...) stay in English, as do all identifiers and code
  in backticks. The surrounding prose is in the native language.
- Indian languages are written in their native script; English words stay in
  Latin script inside it. German is written as German with English
  technical terms ("Denglisch").
- Every requirement of the English text is kept, including the ones the
  bugs hinge on: counting from 1 / dates from 1 January, the tie rule
  (smallest position / earliest date), "greater than T", "some pair of
  consecutive elements", and that the list may be empty or have one element.

Keys are the native-language codes from the study intake survey
(NATIVE_LANGUAGES in frontend/src/components/StudyIntro.jsx).
"""

CODE_MIXED = {
    "P1": {
        "direct": {
            "te": (
                "`has_large_change(readings, T)` అనే function రాయండి. ఇది integers "
                "ఉన్న `readings` అనే list ని, ఒక positive integer `T` ని తీసుకుంటుంది. "
                "`readings` లో ఏదైనా ఒక consecutive elements pair మధ్య absolute "
                "difference `T` కంటే greater అయితే `True` return చేస్తుంది, లేకపోతే "
                "`False` return చేస్తుంది. List empty గా ఉండొచ్చు, లేదా అందులో ఒకే ఒక "
                "element ఉండొచ్చు."
            ),
            "ta": (
                "`has_large_change(readings, T)` என்ற function-ஐ எழுதுங்கள். இது "
                "integers கொண்ட `readings` என்ற list-ஐயும், ஒரு positive integer "
                "`T`-ஐயும் எடுத்துக்கொள்ளும். `readings`-இல் ஏதாவது ஒரு consecutive "
                "elements pair-க்கு இடையிலான absolute difference `T`-ஐ விட greater ஆக "
                "இருந்தால் `True` return செய்யும், இல்லையென்றால் `False` return "
                "செய்யும். List empty ஆக இருக்கலாம், அல்லது அதில் ஒரே ஒரு element "
                "மட்டும் இருக்கலாம்."
            ),
            "hi": (
                "एक function `has_large_change(readings, T)` लिखिए जो integers की एक "
                "list `readings` और एक positive integer `T` लेता है। अगर `readings` के "
                "किसी भी consecutive elements के pair का absolute difference `T` से "
                "greater है, तो यह `True` return करता है, वरना `False`। List empty हो "
                "सकती है या उसमें सिर्फ़ एक element हो सकता है।"
            ),
            "gu": (
                "`has_large_change(readings, T)` નામનું function લખો, જે integers ની "
                "એક list `readings` અને એક positive integer `T` લે છે. જો `readings` "
                "ના કોઈ પણ consecutive elements ની pair વચ્ચેનો absolute difference "
                "`T` કરતાં greater હોય, તો તે `True` return કરે છે, નહીં તો `False`. "
                "List empty હોઈ શકે છે અથવા તેમાં ફક્ત એક જ element હોઈ શકે છે."
            ),
            "de": (
                "Schreibe eine function `has_large_change(readings, T)`, die eine list "
                "von integer `readings` und einen positive integer `T` nimmt. Sie "
                "returnt `True`, wenn die absolute difference zwischen irgendeinem pair "
                "von consecutive elements von `readings` greater als `T` ist, und sonst "
                "`False`. Die list darf empty sein oder nur ein einziges element "
                "enthalten."
            ),
        },
        "contextualized": {
            "te": (
                "ఒక hospital లోని patient monitor, patient యొక్క heart rate ని beats "
                "per minute (bpm) లో, ప్రతి second కి ఒకసారి record చేస్తుంది. Healthy "
                "heart rate ఒక second నుండి తర్వాతి second కి కొంచెం మాత్రమే "
                "మారుతుంది. ఏవైనా రెండు consecutive readings మధ్య heart rate ఎప్పుడైనా "
                "`T` bpm కంటే ఎక్కువ మారితే, nurse ఆ recording ని review చేయాలి అని "
                "hospital clinical guidelines చెబుతున్నాయి: sudden drop అంటే heart fail "
                "అవుతోందని అర్థం కావచ్చు, sudden rise అంటే patient distress లో "
                "ఉన్నారని అర్థం కావచ్చు. Recording empty గా ఉండొచ్చు లేదా అందులో ఒకే "
                "ఒక reading ఉండొచ్చు, ఉదాహరణకు monitor ని ఇప్పుడే attach చేసినప్పుడు. "
                "Readings list (whole numbers) ని, threshold `T` (ఒక positive whole "
                "number) ని తీసుకుని, recording కి review అవసరమైతే `True`, లేకపోతే "
                "`False` return చేసే `has_large_change(readings, T)` అనే function "
                "రాయండి."
            ),
            "ta": (
                "ஒரு hospital-இன் patient monitor, ஒரு patient-இன் heart rate-ஐ beats "
                "per minute (bpm)-இல், ஒவ்வொரு second-க்கும் ஒரு முறை record செய்கிறது. "
                "Healthy heart rate ஒரு second-இலிருந்து அடுத்த second-க்கு கொஞ்சம் "
                "மட்டுமே மாறும். ஏதாவது இரண்டு consecutive readings-க்கு இடையில் heart "
                "rate எப்போதாவது `T` bpm-ஐ விட அதிகமாக மாறினால், nurse அந்த "
                "recording-ஐ review செய்ய வேண்டும் என்று hospital-இன் clinical "
                "guidelines சொல்கின்றன: திடீர் drop என்றால் heart fail ஆகிறது என்று "
                "அர்த்தமாக இருக்கலாம், திடீர் rise என்றால் patient distress-இல் "
                "இருக்கிறார் என்று அர்த்தமாக இருக்கலாம். Recording empty ஆக இருக்கலாம் "
                "அல்லது அதில் ஒரே ஒரு reading மட்டும் இருக்கலாம், உதாரணமாக monitor "
                "இப்போதுதான் attach செய்யப்பட்டிருந்தால். Readings list (whole numbers) "
                "மற்றும் threshold `T` (ஒரு positive whole number) ஆகியவற்றை "
                "எடுத்துக்கொண்டு, recording-க்கு review தேவைப்பட்டால் `True`, "
                "இல்லையென்றால் `False` return செய்யும் `has_large_change(readings, T)` "
                "என்ற function-ஐ எழுதுங்கள்."
            ),
            "hi": (
                "एक hospital का patient monitor हर second एक बार patient का heart rate, "
                "beats per minute (bpm) में, record करता है। एक healthy heart rate एक "
                "second से अगले second तक बस थोड़ा-सा ही बदलता है। Hospital की clinical "
                "guidelines कहती हैं कि अगर किन्हीं भी दो consecutive readings के बीच "
                "heart rate कभी भी `T` bpm से ज़्यादा बदलता है, तो nurse को उस recording "
                "को review करना होगा: अचानक drop का मतलब हो सकता है कि heart fail हो "
                "रहा है, और अचानक rise का मतलब हो सकता है कि patient distress में है। "
                "Recording empty हो सकती है या उसमें सिर्फ़ एक reading हो सकती है, जैसे "
                "अगर monitor अभी-अभी लगाया गया हो। एक function "
                "`has_large_change(readings, T)` लिखिए जो readings की list (whole "
                "numbers) और threshold `T` (एक positive whole number) लेता है, और अगर "
                "recording को review की ज़रूरत है तो `True` return करता है, वरना `False`।"
            ),
            "gu": (
                "એક hospital નું patient monitor દર second એક વાર patient નો heart "
                "rate, beats per minute (bpm) માં, record કરે છે. Healthy heart rate એક "
                "second થી બીજી second સુધી ફક્ત થોડો જ બદલાય છે. Hospital ની clinical "
                "guidelines કહે છે કે જો કોઈ પણ બે consecutive readings વચ્ચે heart rate "
                "ક્યારેય `T` bpm કરતાં વધારે બદલાય, તો nurse એ તે recording ને review "
                "કરવું જ પડે: અચાનક drop નો અર્થ હોઈ શકે કે heart fail થઈ રહ્યું છે, "
                "અને અચાનક rise નો અર્થ હોઈ શકે કે patient distress માં છે. Recording "
                "empty હોઈ શકે છે અથવા તેમાં ફક્ત એક જ reading હોઈ શકે છે, ઉદાહરણ તરીકે "
                "જો monitor હમણાં જ attach કર્યું હોય. `has_large_change(readings, T)` "
                "નામનું function લખો, જે readings ની list (whole numbers) અને threshold "
                "`T` (એક positive whole number) લે છે, અને જો recording ને review ની "
                "જરૂર હોય તો `True` return કરે છે, નહીં તો `False`."
            ),
            "de": (
                "Der patient monitor eines Krankenhauses recordet die heart rate eines "
                "Patienten in beats per minute (bpm), einmal pro second. Eine gesunde "
                "heart rate ändert sich von einer second zur nächsten nur leicht. Die "
                "clinical guidelines des Krankenhauses sagen, dass eine nurse eine "
                "recording reviewen muss, wenn sich die heart rate zwischen zwei "
                "consecutive readings jemals um mehr als `T` bpm ändert: ein "
                "plötzlicher drop kann bedeuten, dass das Herz versagt, und ein "
                "plötzlicher rise kann bedeuten, dass der Patient in distress ist. Eine "
                "recording darf empty sein oder nur ein einziges reading enthalten, zum "
                "Beispiel wenn der monitor gerade erst angeschlossen wurde. Schreibe "
                "eine function `has_large_change(readings, T)`, die die list der "
                "readings (whole numbers) und den threshold `T` (eine positive whole "
                "number) nimmt und `True` returnt, wenn die recording ein review "
                "braucht, und sonst `False`."
            ),
        },
    },
    "P2": {
        "direct": {
            "te": (
                "Numbers ఉన్న ఒక non-empty list ని తీసుకుని, దానిలోని largest value "
                "యొక్క position ని return చేసే `warmest(temps)` రాయండి; positions ని 1 "
                "నుండి లెక్కించాలి. Largest value ఒకటి కంటే ఎక్కువ సార్లు వస్తే, "
                "వాటిలో smallest position ని return చేయండి."
            ),
            "ta": (
                "Numbers கொண்ட ஒரு non-empty list-ஐ எடுத்துக்கொண்டு, அதன் largest "
                "value-இன் position-ஐ return செய்யும் `warmest(temps)`-ஐ எழுதுங்கள்; "
                "positions-ஐ 1-இலிருந்து எண்ண வேண்டும். Largest value ஒன்றுக்கு "
                "மேற்பட்ட முறை வந்தால், அவற்றில் smallest position-ஐ return "
                "செய்யுங்கள்."
            ),
            "hi": (
                "`warmest(temps)` लिखिए जो numbers की एक non-empty list लेता है और "
                "उसकी largest value की position return करता है, positions को 1 से "
                "गिनते हुए। अगर largest value एक से ज़्यादा बार आती है, तो ऐसी सबसे "
                "छोटी (smallest) position return कीजिए।"
            ),
            "gu": (
                "`warmest(temps)` લખો, જે numbers ની એક non-empty list લે છે અને તેની "
                "largest value ની position return કરે છે; positions ને 1 થી ગણવાની "
                "છે. જો largest value એક કરતાં વધુ વાર આવે, તો એમાંથી સૌથી નાની "
                "(smallest) position return કરો."
            ),
            "de": (
                "Schreibe `warmest(temps)`, das eine non-empty list von numbers nimmt "
                "und die position ihres largest value returnt, wobei die positions ab 1 "
                "gezählt werden. Wenn der largest value mehr als einmal vorkommt, "
                "returne die kleinste (smallest) solche position."
            ),
        },
        "contextualized": {
            "te": (
                "India లో మనుషులు నివసించే అత్యంత చల్లని ప్రదేశాలలో ఒకటైన Leh లోని ఒక "
                "weather station, January లో ప్రతి రాత్రి యొక్క lowest temperature ని "
                "degrees Celsius లో, ఒక decimal place వరకు record చేస్తుంది. List లో "
                "కనీసం 1 entry ఉంటుంది; అది 1 January రాత్రితో మొదలవుతుంది, ప్రతి "
                "రాత్రికి ఒక entry ఉంటుంది, చివరిగా record చేసిన రాత్రి వరకు. ఏ రాత్రి "
                "అత్యంత warm గా ఉందో district administration తెలుసుకోవాలనుకుంటోంది. "
                "List ని తీసుకుని, అత్యంత warm రాత్రి యొక్క January date ని return "
                "చేసే `warmest(temps)` రాయండి. ఒకటి కంటే ఎక్కువ రాత్రులు సమానంగా warm "
                "గా ఉంటే, earliest date ని return చేయండి."
            ),
            "ta": (
                "India-வில் மக்கள் வாழும் மிகக் குளிரான இடங்களில் ஒன்றான Leh-இல் உள்ள "
                "ஒரு weather station, January மாதத்தில் ஒவ்வொரு இரவின் lowest "
                "temperature-ஐ degrees Celsius-இல், ஒரு decimal place வரை record "
                "செய்கிறது. List-இல் குறைந்தது 1 entry இருக்கும்; அது 1 January இரவில் "
                "தொடங்கி, ஒவ்வொரு இரவுக்கும் ஒரு entry என்று, கடைசியாக record "
                "செய்யப்பட்ட இரவு வரை இருக்கும். எந்த இரவு மிகவும் warm ஆக இருந்தது "
                "என்று district administration தெரிந்துகொள்ள விரும்புகிறது. List-ஐ "
                "எடுத்துக்கொண்டு, மிகவும் warm ஆன இரவின் January date-ஐ return செய்யும் "
                "`warmest(temps)`-ஐ எழுதுங்கள். ஒன்றுக்கு மேற்பட்ட இரவுகள் சமமாக warm "
                "ஆக இருந்தால், earliest date-ஐ return செய்யுங்கள்."
            ),
            "hi": (
                "Leh में, जो India की सबसे ठंडी आबादी वाली जगहों में से एक है, एक "
                "weather station January में हर रात का lowest temperature, degrees "
                "Celsius में, एक decimal place तक record करता है। List में कम से कम 1 "
                "entry है, यह 1 January की रात से शुरू होती है और हर रात की एक entry "
                "है, सबसे recent record की गई रात तक। District administration जानना "
                "चाहता है कि कौन-सी रात सबसे warm थी। `warmest(temps)` लिखिए जो list "
                "लेता है और सबसे warm रात की January की date return करता है। अगर एक से "
                "ज़्यादा रातें बराबर warm थीं, तो सबसे पहली (earliest) date return "
                "कीजिए।"
            ),
            "gu": (
                "India ની સૌથી ઠંડી વસવાટવાળી જગ્યાઓમાંની એક, Leh માં એક weather "
                "station January ની દરેક રાતનું lowest temperature, degrees Celsius "
                "માં, એક decimal place સુધી record કરે છે. List માં ઓછામાં ઓછી 1 entry "
                "છે; તે 1 January ની રાતથી શરૂ થાય છે અને દરેક રાત માટે એક entry છે, "
                "છેલ્લે record થયેલી રાત સુધી. District administration જાણવા માંગે છે "
                "કે કઈ રાત સૌથી warm હતી. `warmest(temps)` લખો, જે list લે છે અને સૌથી "
                "warm રાતની January ની date return કરે છે. જો એક કરતાં વધુ રાતો સરખી "
                "warm હોય, તો સૌથી પહેલી (earliest) date return કરો."
            ),
            "de": (
                "Eine weather station in Leh, einem der kältesten bewohnten Orte "
                "Indiens, recordet im January die lowest temperature jeder Nacht, in "
                "degrees Celsius auf eine decimal place genau. Die list hat mindestens "
                "1 entry, beginnt mit der Nacht des 1. January und hat eine entry pro "
                "Nacht, bis zur zuletzt recordeten Nacht. Die district administration "
                "möchte wissen, welche Nacht die wärmste war. Schreibe `warmest(temps)`, "
                "das die list nimmt und das date im January der wärmsten Nacht returnt. "
                "Wenn mehr als eine Nacht gleich warm war, returne das earliest date."
            ),
        },
    },
}
