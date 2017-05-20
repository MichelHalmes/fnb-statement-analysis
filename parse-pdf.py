
import re
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from os import listdir
import csv

import PyPDF2






RE_MONTHS = r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'

REGEX = r"(?P<date1>\d{2}%months%)"\
        r"(?P<core>[\w \*\-&/'\.#]*)"\
        r"(?P<amt>(\d{1,2}.)?\d{1,3}\.\d{2}(Cr)?)"\
        r"(?P<tot>\d{2,3},\d{3}\.\d{2})Cr(\d\.\d{2})?"

REGEX = REGEX.replace(r'%months%', RE_MONTHS)


TYPES =["POS International Purchase Chq", "POS Purchase Chq Card", "Internet Pmt To", 
        "Magtape Debit", "ATM Cash", "Chq Card Fuel Purchase", "FNB App Payment To",
        "Notification - Email", "#", "Refund Chq Card Purchase", "FNB OB Pmt", "Magtape Credit"]

TYPE_REGEX = r"^(?P<type>%types%)".replace('%types%', '|'.join(TYPES))

CORE_END_REGEX =  r"(?P<card>(412752(\*|500081)2632(  )?)?)"\
                    r"(?P<date2>(\d{2} %months%)??)"\
                    r"(?P<carry>(\d{1,2})?)$".replace(r'%months%', RE_MONTHS)

def decompose_core(core):
    m = re.search(TYPE_REGEX, core)
    assert m
    typ = m.group(0)
    core = core[len(typ):]

    
    m = re.search(CORE_END_REGEX, core)
    if m and len(m.group(0)):
        card = m.group('card')
        date2 = m.group('date2')
        if date2:
            date2 = datetime.strptime(date2, "%d %b")
        carry = m.group('carry')
        core = core[:-len(m.group(0))]
    else:
        card = date2 = carry = '' 
        print "No end for core:", core


    return typ, card, date2, carry, core



def decompose_record(match, prev_total, month_to_year):
    print "\n", match.group(0)
    date = match.group('date1')
    date = datetime.strptime(date, "%d%b")

    typ, card, date2, carry, desc = decompose_core(match.group('core'))

    amount = carry + match.group('amt').replace(',', '')
    if amount.endswith("Cr"):
        amount = float(amount.replace('Cr', ''))
    else:
        amount = - float(amount)

    total = match.group('tot').replace(',', '')
    total = float(total)

    if prev_total and not round(amount,5) == round(total-prev_total,5):
        delta = total-prev_total      
        amt_str = str(abs(amount))
        delta_str = str(abs(delta))
        assert amt_str.endswith(delta_str)
        amount = delta
        print ">>> PrevTot({}) + Amount({}) != Total({}) --> {}".format(prev_total, amount, total, total-prev_total-amount)
    

    record = {  'date': set_record_year(date, month_to_year),
                'type': typ,
                'card': card,
                # 'date2': set_record_year(date2, month_to_year),
                'description': desc,
                'amount': amount,
                'total': total}

    record['class'] = classify(record)

    return record

def set_record_year(date, month_to_year):
    if not date:
        return date
    return date.replace(year=month_to_year[date.month])


DESCRIPTION_CLASS = {
    'public_tansport': ['uber', 'myciti'],
    'foodlovers': ['foodlovers', 'food lovers'],
    'groceries': ['woolworths', 'spar', 'pick n pay', 'checkers'],
    'salary': ['axio02'],
    'fixed': ['afrihost', 'outsurance', 'epic3', 'economist'],
    'rent': ['rent michel'],
    'booze_bar': ['liquor', 'tops', 'brew', 'bar', 'wine', 'cafe'],
    'events': ['quicket', 'webticket'],
    'takealot': ['takealot']

    }

def classify(record):
    for clas, keywords in DESCRIPTION_CLASS.iteritems():
        for key in keywords:
            if key in record['description'].lower():
                return clas 


    if record['type'] in ["Magtape Credit", "Internet Pmt To", "FNB OB Pmt", "FNB App Payment To"]:
        return "payments"
    if record['type'] == "ATM Cash":
        return "cash"
    if record['type'] == "Chq Card Fuel Purchase":
        return "fuel"
    if record['amount'] < -600:
        return 'large_expense'




  





def decompose_file(file_path, file_date):
    records = []
    pdfFileObj = open(file_path, 'rb')
    pdfReader = PyPDF2.PdfFileReader(pdfFileObj)
    for page_nb in range(1, pdfReader.numPages):
        pageObj = pdfReader.getPage(page_nb)
        text = pageObj.extractText()

        prev_end = None
        prev_total = None
        for match in re.finditer(REGEX, text, re.S):
            record =  decompose_record(match, prev_total, file_date)
            print record
            records.append(record)
            prev_total = record['total']
            if prev_end:
                assert prev_end == match.start()
            prev_end = match.end()
    return records

def main():
    all_records = []

    for file_name in listdir('./statements'):
        file_date = file_name[-14:-4]
        file_date = datetime.strptime(file_date, '%Y-%m-%d')
        month_to_year = {}
        for delta_month in range(3):
            date = file_date - relativedelta(months=delta_month)
            month_to_year[date.month] = date.year

        records = decompose_file('./statements/'+file_name, month_to_year)
        all_records += records
        

    with open('records.csv', 'wb') as f:
        dict_writer = csv.DictWriter(f, all_records[0].keys())
        dict_writer.writeheader()
        dict_writer.writerows(all_records)



if __name__=='__main__':
    main()



    



