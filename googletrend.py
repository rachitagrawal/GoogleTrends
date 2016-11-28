# coding:utf-8

import urllib,urllib2,csv,json,re,time,sys,string,math,datetime
from datetime import date

#Starting Sequence number of the file
seq_start = 1000
#Ending sequencer number of the file
seq_end = 1000
#Wait time in seconds
wait_time = 3600
#Number of fields in the input file
num_fields = 11

def make_json_ready(response):
    new_response = string.replace(response, 'new Date', '"new Date')
    response = string.replace(new_response, ')', ')"')
    return response

def date_from(string, format_type):
    month_map = {'JAN':1,'FEB':2,'MAR':3,'APR':4,'MAY':5,'JUN':6,'JUL':7,'AUG':8,'SEP':9,'OCT':10,'NOV':11,'DEC':12}

    if format_type == 1:
        day = string[0:2]
        month = string[2:5]
        year = string[5:]
        return date(int(year),month_map[month],int(day))
    else:
        items = string.split('-')
        return date(int('20'+items[2]),month_map[items[1].upper()],int(items[0]))

def diff_months(d1, d2):
    num_months =  (d2.year - d1.year)*12 + d2.month - d1.month
    if d2.day - d1.day > 0:
        num_months += 1

    return num_months

def get_num_observation(start_date, end_date, frequency):
    num_days = (end_date-start_date).days
    num_months = diff_months(start_date, end_date)
    num_weeks = (int)(math.ceil((end_date-start_date).days / 7.0))

    if num_days <= 90:
        if frequency.lower() == "monthly":
            return num_months
        elif frequency.lower() == "weekly":
            return num_weeks
        else:
            return num_days
    elif num_days > 90 and num_days <= 1080:
        if frequency.lower() == "monthly":
            return num_months
        else:
            return num_weeks
    else:
        return num_months

   
def get_end_date(start_date, end_date, frequency):
    num_days = (end_date-start_date).days

    if num_days <= 90:
        if frequency.lower() == "monthly":
            return 1081
        elif frequency.lower() == "weekly":
            return 91
        else:
            return num_days
    elif num_days > 90 and num_days <= 1080:
        if frequency.lower() == "daily":
            print "Google Trends doesn't support daily data more than 90 days. Generating weekly data"
            return num_days
        elif frequency.lower() == "monthly":
            return 1081
        else:
            return num_days
    else:
        if frequency.lower() == "monthly":
           return num_days
        else:
           print "Google Trends only supports monthly data more than 1080 days. Generating monthly data."
           return 1081


def generate_url_string(start_date, end_date, query_terms, category='0', export_type='3'):

    #If no query terms specified return a null string url
    if not query_terms[0]:
        return ""

    query_string = query_terms[0]
    for query in range(1,5):
        if query_terms[query]:
            query_string += "," + query_terms[query]

    url_date = '{}/{}/{}+{}d'.format(start_date.month,start_date.day,start_date.year,(end_date-start_date).days)
    url = 'http://www.google.com/trends/fetchComponent?'+urllib.urlencode({'q':'"{}"'.format(query_string),'cat':category,'cid':'TIMESERIES_GRAPH_0','export':export_type})
    url += '&date='+url_date

    return url
    
def main( infilename, outfilename ):
    with open(infilename,"rb") as csvfile:
        reader = csv.reader(csvfile,quotechar='#')
        reader.next()
        opener = urllib2.build_opener()
        opener.addheaders = [('Cookie','PREF="ID=fe087197ad8cbd26:FF=0:LD=en-US:TM=1431587741:LM=1431587741:S=fbpFsZq3I2vEAuga"')]
        with open(outfilename,"wb") as outfile:
            csvwriter = csv.writer(outfile,quotechar='#')
            csvwriter.writerow(('ID','company','date','value'))
            for item in reader:
                print "Processing query:", item
                if len(item) != num_fields:
                    raise csv.Error("Incorrect number of fields in the csvfile %s. There should be %d fields" % (infilename,num_fields))

                scores_matrix = []
                dates_matrix = []

                if "-" in item[6]:
                    start_date = date_from(item[6], 2)
                    end_date = date_from(item[7], 2)
                else:
                    start_date = date_from(item[6], 1)
                    end_date = date_from(item[7], 1)
                    
                num_days = get_end_date(start_date, end_date, item[10])
                delta_time = datetime.timedelta(days=num_days)

                cur_start_date = start_date

                num_query_terms = 0
                num_observations = 0
                num_observations_left = get_num_observation(start_date, end_date, item[10])

                #while (end_date-cur_start_date).days > 0:
                new_end_date = cur_start_date + delta_time
                print "Processing for the time period:(%s -- %s)" % (cur_start_date,new_end_date)

                url = generate_url_string(cur_start_date, new_end_date, item[1:6])

                if not url:
                    print "No query term specified"
                else:
                    if item[9] != 'WORLD':
                        url += '&geo='+item[9]
                    try:
                        response = opener.open(url).read()
                        match = re.search(r'{.*}',response)
                        response = match.group(0)

                        if response.find("rows") == -1:
                            print "You have exceeded your hourly quota. Please try after sometime."
                        else:
                            data = json.loads(make_json_ready(response))

                            num_observations = len(data["table"]["rows"])
                            num_query_terms = len(data["table"]["cols"]) - 1

                            for row_num in xrange(num_observations):

                                if row_num < num_observations_left:
                                    scores = [0.0, 0.0, 0.0, 0.0, 0.0]
                                    scores_matrix.append(scores)

                                    cur_date = data["table"]["rows"][row_num]["c"][0]["v"]
                                    date_match = re.search(r'Date\((\d+),(\d+),(\d+)\)',cur_date)
                                    date_string = '{:02d}/{:02d}/{}'.format(int(date_match.group(2))+1, int(date_match.group(3)), date_match.group(1))

                                    dates_matrix.append(date_string)

                                    for cur_query_ind in xrange(num_query_terms):
                                        if "v" in data["table"]["rows"][row_num]["c"][cur_query_ind+1]:
                                            scores_matrix[row_num][cur_query_ind] = data["table"]["rows"][row_num]["c"][cur_query_ind+1]["v"]

                        
                    except Exception,e:
                        print e
                        print "You have exceeded your hourly quota. Please try after sometime."

                #Update variables
                cur_start_date = new_end_date
                num_observations_left = (end_date-cur_start_date).days
                
                for cur_query in xrange(num_query_terms):
                    for cur_entry in xrange(len(scores_matrix)):
                        csvwriter.writerow((item[0], item[cur_query+1], dates_matrix[cur_entry], scores_matrix[cur_entry][cur_query]))        
        #Closing the outfile
        outfile.close()
    #Closing the csvfile
    csvfile.close()

if __name__ == '__main__':
    import sys
    reload(sys)
    sys.setdefaultencoding('utf8')
    try:
        for seq_no in range(seq_start,seq_end+1):
            next_in_file = "infileacq" + `seq_no` + ".csv"
            next_out_file = "outfileacq" + `seq_no` + ".csv"
            print "Processing File : %s" % next_in_file
            main(next_in_file, next_out_file)
            print "Processing Done. Check File %s" % next_out_file
            if seq_no != seq_end:
                print "Waiting for %d secs before next file.\n" % wait_time 
                for i in xrange(51):
                    sys.stdout.write('\r')
                    sys.stdout.write("[%-50s] %d%%" % ('='*i, 2*i))
                    sys.stdout.flush()
                    time.sleep(wait_time/50)
                print '\n'

    except Exception,e:
        print "Unexcepted Error:",e
    raw_input("Enter any key to exit:")
