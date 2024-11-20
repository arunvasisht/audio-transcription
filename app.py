from nicegui import ui, events, Tailwind
import boto3
from dotenv import load_dotenv
from uuid import uuid4
import os, webbrowser

# Load the environment variables
load_dotenv()

# Create AWS S3 client
s3 = boto3.client("s3")
transcribe = boto3.client("transcribe",region_name=os.environ["AWS_REGION"])


def handle_upload(e:events.UploadEventArguments):
    file_path = "Input/" + e.name
    # Store the uploaded file to S3
    upload_response = s3.put_object(
        Key=file_path,
        Body=e.content.read(),
        Bucket=os.environ["BUCKET_NAME"]
    )
    if upload_response["ResponseMetadata"]["HTTPStatusCode"] == 200:
        ui.notify(f"File uploaded successfully to {file_path}",type="positive")
        job_name = str(uuid4())
        s3_uri = f"s3://{os.environ['BUCKET_NAME']}/Input/{e.name}"
        job = transcribe.start_transcription_job(            
                TranscriptionJobName=job_name,
                LanguageCode='es-US',
                Media={
                        'MediaFileUri': s3_uri
                    }
            )
        # has the transcription started?    
        http_code = job["ResponseMetadata"]["HTTPStatusCode"]
        if http_code == 200:
            ui.notify("Transcription Started Successfully!", type="positive")
        else:
            ui.notify("Transcription could not be started!",type="negative")

        print(job)
        # Update the Table
        table.add_row({
            "name":job["TranscriptionJob"]["TranscriptionJobName"],
            "created": str(job["TranscriptionJob"]["CreationTime"].date()),
            "completed":"",
            "status":job["TranscriptionJob"]["TranscriptionJobStatus"]
        })
    else:
        ui.notify(f"Could not upload {e.name}",type="negative")


# User Interface
ui.label("Audio Transcription Demo").style("font-size:200%;font-weight:500")

ui.label("Transcription Jobs").style("font-size:150%;font-weight:500")



table_columns=[
    {"name":"name","label":"Job Name","field":"name"},
    {"name":"created","label":"Created On", "field":"created"},
    {"name":"completed","label":"Completed On","field":"completed"},
    {"name":"status","label":"Status","field":"status"},
    {"name":"action","label":"Actions","field":"action"}
]

jobs = (
    [
        {
            "name":job["TranscriptionJobName"],
            "created": str(job["CreationTime"].date()),
            "completed":str(job["CompletionTime"].date()),
            "status":job["TranscriptionJobStatus"]
        }
        for job in transcribe.list_transcription_jobs()["TranscriptionJobSummaries"]
    ]
    )

table = ui.table(columns=table_columns,rows=jobs,row_key='name', pagination=20).classes("w-full")
table.add_slot('body-cell-status',"""
        <q-td key="status" :props="props">
        <q-badge :color="props.value != 'COMPLETED' ? 'red' : 'green'">
            {{ props.value }}
        </q-badge>
    </q-td> 
""")    

table.add_slot('table')

def download_transcription(job_name):
    job = transcribe.get_transcription_job(TranscriptionJobName = job_name)
    download_filename = job_name + ".json"
    transcript_url = job["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
    webbrowser.open(transcript_url)

    

table.add_slot('body-cell-action', r'''
<q-td key="name" :props="props"> 
    <q-btn v-if="props.row.status === 'COMPLETED'" @click="$parent.$emit('download-click', props.row)" icon="download" flat></q-btn>
</q-td>
''')
table.on('download-click',lambda row: download_transcription(row.args["name"]))

def start_transcription_job():
    with ui.dialog() as dialog, ui.card():
        ui.html("<b>Upload Audio File for Transcription</b>")
        ui.upload(label="Select File", on_upload=handle_upload).props("accept=.wav")
        ui.button('Close', on_click=dialog.close)
    dialog.open()

def update_table():
    jobs = (
    [
        {
            "name":job["TranscriptionJobName"],
            "created": str(job["CreationTime"].date()),
            "completed":str(job["CompletionTime"].date() if job["TranscriptionJobStatus"] == "COMPLETED" else ""),
            "status":job["TranscriptionJobStatus"]
        }
        for job in transcribe.list_transcription_jobs()["TranscriptionJobSummaries"]
    ]
    )
    table.rows = jobs
    table.update()
    print("Table Updated")

with ui.element("div") as div:
    ui.button("Start New Job",on_click=start_transcription_job, icon="start").style("margin-right:10px;")
    ui.button("Refresh List ", icon="refresh", on_click=update_table)

ui.run()