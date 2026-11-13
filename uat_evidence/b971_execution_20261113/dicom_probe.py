"""Synthetic DICOM tests only; NOT a production anonymizer."""
import sys,json,hashlib,subprocess
from pathlib import Path
sys.path.insert(0,str(Path('helpers/pydicom_runtime').resolve()))
import pydicom,numpy as np
from pydicom.dataset import FileDataset,FileMetaDataset,Dataset
from pydicom.uid import ExplicitVRLittleEndian,SecondaryCaptureImageStorage,generate_uid
from PIL import Image,ImageDraw,ImageFont
out=Path(__file__).parent/'synthetic_dicom';out.mkdir(exist_ok=True)
def create(name,metadata=False,pixels=False,flag='NO'):
 im=Image.new('L',(768,256),0);d=ImageDraw.Draw(im)
 d.rectangle((220,100,540,230),fill=90)
 if pixels:d.text((20,25),'SYNTHETIC PATIENT MARKER 971',font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',28),fill=255)
 else:d.text((20,25),'UAT PHANTOM 971',font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',28),fill=255)
 meta=FileMetaDataset();meta.TransferSyntaxUID=ExplicitVRLittleEndian;meta.MediaStorageSOPClassUID=SecondaryCaptureImageStorage;meta.MediaStorageSOPInstanceUID=generate_uid();meta.ImplementationClassUID=generate_uid()
 ds=FileDataset(str(out/name),{},file_meta=meta,preamble=b'\0'*128)
 ds.SOPClassUID=meta.MediaStorageSOPClassUID;ds.SOPInstanceUID=meta.MediaStorageSOPInstanceUID;ds.StudyInstanceUID=generate_uid();ds.SeriesInstanceUID=generate_uid()
 ds.Modality='OT';ds.PatientName='SYNTHETIC^PATIENT971' if metadata else '';ds.PatientID='SYNTHETIC-MRN-971' if metadata else '';ds.PatientBirthDate='19800102' if metadata else ''
 ds.BurnedInAnnotation=flag;ds.Rows=256;ds.Columns=768;ds.SamplesPerPixel=1;ds.PhotometricInterpretation='MONOCHROME2';ds.BitsAllocated=8;ds.BitsStored=8;ds.HighBit=7;ds.PixelRepresentation=0;ds.PixelData=np.asarray(im).tobytes()
 if metadata:
  nested=Dataset();nested.PatientName='SYNTHETIC^NESTED';ds.RequestAttributesSequence=[nested];ds.add_new((0x0011,0x0010),'LO','SYNTHETIC_PRIVATE');ds.add_new((0x0011,0x1010),'LO','SYNTHETIC-MRN-PRIVATE')
 pydicom.dcmwrite(ds.filename,ds,enforce_file_format=True);im.save(out/(name+'.png'));return out/name
cases=[('clean971.dcm',False,False,'NO'),('metadata971.dcm',True,False,'NO'),('burned971.dcm',False,True,'YES'),('mislabelled971.dcm',False,True,'NO'),('SYNTHETIC-MRN-971.dcm',False,False,'NO')]
results=[]
for name,meta,pix,flag in cases:
 f=create(name,meta,pix,flag);ds=pydicom.dcmread(f)
 sensitive=[e.keyword or str(e.tag) for e in ds.iterall() if (e.keyword in ['PatientName','PatientID','PatientBirthDate'] and str(e.value)) or e.tag.is_private]
 text=subprocess.run(['tesseract',str(out/(name+'.png')),'stdout','--psm','6'],capture_output=True,text=True,check=True).stdout
 burned='PATIENT' in text.upper();filename='MRN' in f.name.upper();reject=bool(sensitive or burned or filename or ds.BurnedInAnnotation!='NO')
 assert reject==(name!='clean971.dcm'),name
 assert np.array_equal(ds.pixel_array,np.asarray(Image.open(out/(name+'.png'))))
 results.append(dict(file=name,sha256=hashlib.sha256(f.read_bytes()).hexdigest(),metadata_findings=sensitive,burned_marker_detected=burned,filename_marker_detected=filename,declared_burned_in=flag,decision='REJECT' if reject else 'CLEAN_SYNTHETIC_CONTROL',decoded_pixels_verified=True))
(out/'results.json').write_text(json.dumps({'scope':'LOCAL_SYNTHETIC_DICOM_ONLY','pydicom_version':pydicom.__version__,'results':results,'passed':len(results),'real_patient_data':False,'external_upload':False,'limitations':['OCR may miss arbitrary burned-in text; manual image inspection still required.','This is detection on controlled fixtures, not clinical DICOM anonymization validation.','No EDC upload/receipt/role workflow has been exercised.'],'formal_pass_delta':0},ensure_ascii=False,indent=2)+'\n')
print('5 synthetic DICOM detection/decoding scenarios passed; no external upload')
