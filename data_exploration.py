import requests
from bs4 import BeautifulSoup
import pandas as pd
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
import time
import csv
import numpy as np
import os
import zipfile


def Extract_Forum_data():

    # driver_path = '/Users/prathamsolanki/PycharmProjects/DSCi-560/msedgedriver'
    # output_file_path = "forum_page.html"
    # csv_output_path = 'forum_extracted_data.csv'
    # service = EdgeService(executable_path=driver_path)
    # driver = webdriver.Edge(service=service)

    driver_path = '/snap/bin/firefox.geckodriver'
    output_file_path ='/home/prathamuser/Desktop/prathamsolanki_3242692358/data/raw_data/forum_page.html'
    csv_output_path = '/home/prathamuser/Desktop/prathamsolanki_3242692358/data/processed_data/forum_extracted_data.csv'
    service = Service(executable_path=driver_path)
    driver = webdriver.Firefox(service=service)

    url = "https://discuss.huggingface.co/t/fine-tune-llms-on-pdf-documents/71374"
    # url ="https://discuss.huggingface.co/t/how-do-i-create-a-image-segmentation-dataset/23123"

    def fetch_html(url,driver_path,output_path,service,driver):

        try:
            driver.get(url)

            driver.implicitly_wait(10)
            time.sleep(20)

            html_content = driver.page_source

            html_parsed = BeautifulSoup(html_content, 'html.parser')

            with open(output_path, "w", encoding="utf-8") as file:
                file.write(html_parsed.prettify())

        finally:
            driver.quit()

        return None

    def read_html(output_path):
        with open(output_path, "r", encoding="utf-8") as file:
            html_list = file.readlines()

        html_str = "\n".join(html_list)

        html_parsed = BeautifulSoup(html_str, 'html.parser')

        return html_parsed

    def extract_data(html_parsed):
        all_responses_list = []
        question_dict = {}
        related_topics_dict = {}

        title = html_parsed.find('a', class_="fancy-title").get_text(strip=True)
        question_dict['title']=title

        post_stream = html_parsed.find('div',class_='post-stream')

        def get_question_dict(article,main_dict):
            row = article.find('div',class_= 'row')

            name = row.find('span', class_="first username").find('a', class_="").get_text(strip=True)
            main_dict['name'] = name

            date_time = row.find('span',class_="relative-date").get('title')
            main_dict['date_time'] =date_time

            content_text_list = [text.get_text(strip=True) for text in row.find('div',class_='regular contents').find('div',class_="cooked").find_all('p')]
            main_dict['content_text_list'] = content_text_list

            page_stats = article.\
                find('div',class_='topic-map --op').find('section',class_='topic-map__contents').\
                find('div',class_='topic-map__stats --many-stats').\
                find_all('button')

            for page_stat in page_stats:
                main_dict[page_stat.find('span',class_='topic-map__stat-label').get_text(strip=True)] = page_stat.find('span',class_='number').get_text(strip=True)

            return question_dict


        responses = post_stream.find_all('article')

        for response in responses:
            if response.get('id')=='post_1':
                article1 = post_stream.find('article',id = "post_1")
                question_dict = get_question_dict(article1,question_dict)
                # print(question_dict)

            else:
                individual_response_dict = {}
                content_list= []
                individual_response_dict['post_no'] = response.get('id')

                def get_name(response):
                    #Get Name
                    name_tag = response. \
                            find('div', class_='row'). \
                            find('div', class_='names trigger-user-card')

                    if name_tag.find('span',class_= 'first username') is not None:
                        name = name_tag.find('span', class_='first username').find('a').get_text(strip=True)

                    elif name_tag.find('span',class_='first username new-user') is not None:
                        name = name_tag.find('span', class_='first username new-user').find('a').get_text(strip=True)

                    elif name_tag.find('span', class_='first username staff moderator') is not None:
                        name = name_tag.find('span', class_='first username staff moderator').find('a').get_text(strip=True)

                    else:
                        name = ""

                    return name

                def get_content(response):
                    content_tag = response.find('div', class_="cooked")
                    content_list = [text.get_text(strip=True) for text in content_tag.find_all(['p', 'li', 'strong', 'a'])]

                    return content_list

                def get_date_time(response):
                    return response.find('span',class_='relative-date').get('title')

                def get_like(response):
                    if response.find('span',class_='reactions-counter') is not None:
                        return response.find('span',class_='reactions-counter').get_text(strip=True)

                    else:
                        return '0'


                # Etract name
                individual_response_dict['name'] = get_name(response)

                #Extract content
                individual_response_dict['content'] = get_content(response)

                #Extract Date time
                individual_response_dict['date_time'] =get_date_time(response)

                # get like count
                individual_response_dict['likes'] = get_like(response)



                # print(individual_response_dict)
                #appending individual response dict to list
                all_responses_list.append(individual_response_dict)


        return question_dict,all_responses_list

    def write_to_csv(question_dict,all_responses_list):
        with open(csv_output_path , mode='w', newline='', encoding='utf-8') as forum_file:
            forum_writer = csv.writer(forum_file)

            #writing column names
            forum_writer.writerow(['time_stamp', 'title', 'name','post','views', 'likes', 'links', 'users'])

            forum_writer.writerow([question_dict['date_time'],question_dict['title'],question_dict['name'],question_dict['content_text_list'],question_dict['views'],question_dict['likes'],question_dict['links'],question_dict['users']])

            for response in all_responses_list:
                forum_writer.writerow([response['date_time'],question_dict['title'],response['name'],response['content'],question_dict['views'],response['likes'],np.nan,np.nan])

        return None

    def basic_operations(csv_output_path):
        df = pd.read_csv(csv_output_path)
        pd.set_option('display.max_columns', None)

        print("Columns",df.columns)
        print('Shape of dataset',df.shape)
        print('Null values:','\n',df.isnull().sum())
        print(df.head())



    #Get html
    fetch_html(url,driver_path,output_file_path,service,driver)
    print("HTML fetched successfully")

    #parse
    html_parsed = read_html(output_file_path)
    print("Data Parsed successfully")

    #Extract elements
    question_dict,all_responses_list = extract_data(html_parsed)
    print("Data extracted successfully")


    #write to csv
    write_to_csv(question_dict,all_responses_list)
    print("Data written to CSV successfully")

    #basic operations
    basic_operations(csv_output_path)



    return None


def Extract_CSV_data():
    # output_path = '/home/prathamuser/Desktop/prathamsolanki_3242692358/data/processed_data/extracted_csv.csv'
    output_path = 'extracted_csv.csv'

    kaggle_username = 'prathamsolanki1202'
    kaggle_key = 'b8fb55cfc4e620e3fd0e33da4b374d10'


    kaggle_json_path = 'kaggle.json'
    with open(kaggle_json_path, 'w') as f:
        f.write(f'{{"username":"{kaggle_username}","key":"{kaggle_key}"}}')


    os.environ['KAGGLE_CONFIG_DIR'] = os.getcwd()


    dataset_identifier = 'jaceprater/smokers-health-data'

    download_dir = 'temp_download'

    os.makedirs(download_dir, exist_ok=True)

    os.system(f'kaggle datasets download -d {dataset_identifier} -p {download_dir}')

    zip_file = [f for f in os.listdir(download_dir) if f.endswith('.zip')][0]
    zip_file_path = os.path.join(download_dir, zip_file)

    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        zip_ref.extractall(download_dir)

    csv_file = [f for f in os.listdir(download_dir) if f.endswith('.csv')][0]
    csv_file_path = os.path.join(download_dir, csv_file)

    os.rename(csv_file_path, output_path)

    os.remove(zip_file_path)
    os.rmdir(download_dir)
    os.remove(kaggle_json_path)

    print(f'Dataset downloaded and saved to: {output_path}')

    def basic_operations(csv_output_path):
        df = pd.read_csv(csv_output_path)
        pd.set_option('display.max_columns', None)

        print("Columns", df.columns)
        print('Shape of dataset', df.shape)
        print('Null values:', '\n', df.isnull().sum())
        print(df.tail())

    basic_operations(output_path)




    return None



#Main

Extract_Forum_data()

Extract_CSV_data()