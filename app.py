from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import os
from pathlib import Path
from typing import Optional
import base64
import traceback
import sys

# Define absolute path for temp directory
TEMP_DIR = Path('/app/temp')

app = FastAPI(
    title="LilyPond API",
    description="API for converting music notation to images",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LilyPondInput(BaseModel):
    content: str
    version: Optional[str] = "2.24.0"

class LilyPondResponse(BaseModel):
    image: str
    format: str = "png"

class BinaryInput(BaseModel):
    content: str
    version: Optional[str] = "2.24.0"

def create_lily_file(content: str, filename: Path, version: str = "2.24.0") -> None:
    try:
        lily_content = f'\\version "{version}"\n'
        lily_content += f'{content}\n'
        
        # Ensure directory exists and has proper permissions
        filename.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filename, 'w') as f:
            f.write(lily_content)
            
        # Set proper permissions
        os.chmod(filename, 0o666)
    except Exception as e:
        raise Exception(f"Error creating LilyPond file: {str(e)}")

@app.post("/convert", 
    response_model=LilyPondResponse,
    summary="Convert music notation to base64 image",
    description="Takes LilyPond notation and returns base64 encoded image")
async def convert_to_image(data: LilyPondInput):
    lily_file = None
    pdf_file = None
    png_file = None
    
    try:
        # Create temporary file paths
        TEMP_DIR.mkdir(exist_ok=True)
        
        base_name = 'output'
        lily_file = TEMP_DIR.absolute() / f'{base_name}.ly'
        pdf_file = TEMP_DIR.absolute() / f'{base_name}.pdf'
        png_file = TEMP_DIR.absolute() / f'{base_name}.png'

        print(f"Processing request with content: {data.content}")  # Debug log

        # Create LilyPond file
        create_lily_file(data.content, lily_file, data.version)
        print(f"Created LilyPond file at: {lily_file}")  # Debug log

        # Check if lilypond is installed
        lilypond_check = subprocess.run(['which', 'lilypond'], capture_output=True, text=True)
        if lilypond_check.returncode != 0:
            raise Exception(f"LilyPond is not installed. Path check output: {lilypond_check.stderr}")

        # Run LilyPond with full error capture
        print("Running LilyPond...")  # Debug log
        process = subprocess.run(
            ['lilypond', '--pdf', '-o', str(TEMP_DIR.absolute() / base_name), str(lily_file)],
            capture_output=True,
            text=True
        )
        if process.returncode != 0:
            error_msg = f"LilyPond error:\nStdout: {process.stdout}\nStderr: {process.stderr}"
            print(error_msg)  # Debug log
            raise Exception(error_msg)

        # Check if ImageMagick is installed
        convert_check = subprocess.run(['which', 'convert'], capture_output=True, text=True)
        if convert_check.returncode != 0:
            raise Exception(f"ImageMagick is not installed. Path check output: {convert_check.stderr}")

        # Convert PDF to PNG with full error capture
        print("Converting PDF to PNG...")  # Debug log
        process = subprocess.run(
            ['convert', '-density', '300', str(pdf_file), str(png_file)],
            capture_output=True,
            text=True
        )
        if process.returncode != 0:
            error_msg = f"ImageMagick error:\nStdout: {process.stdout}\nStderr: {process.stderr}"
            print(error_msg)  # Debug log
            raise Exception(error_msg)

        # Verify files exist
        if not pdf_file.exists():
            raise Exception(f"PDF file was not created at {pdf_file}")
        if not png_file.exists():
            raise Exception(f"PNG file was not created at {png_file}")

        # Read the PNG file
        print("Reading PNG file...")  # Debug log
        with open(png_file, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')

        return LilyPondResponse(image=image_data)

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        error_details = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        print(f"Error occurred:\n{error_details}")  # Server log
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "traceback": error_details,
                "type": str(exc_type)
            }
        )

    finally:
        # Clean up temporary files
        for file in [lily_file, pdf_file, png_file]:
            if file and file.exists():
                try:
                    os.remove(file)
                    print(f"Cleaned up {file}")  # Debug log
                except Exception as e:
                    print(f"Error cleaning up {file}: {e}")  # Debug log

@app.post("/convert/txt", 
    response_model=LilyPondResponse,
    summary="Convert LilyPond text file to base64 image",
    description="Takes a .txt file containing LilyPond notation and returns base64 encoded image")
async def convert_txt_to_image(
    file: UploadFile = File(...),
    version: str = "2.24.0"
):
    if not file.filename.endswith('.txt'):
        raise HTTPException(status_code=400, detail="File must be a .txt file")

    lily_file = None
    pdf_file = None
    png_file = None
    
    try:
        # Create temporary file paths
        TEMP_DIR.mkdir(exist_ok=True)
        
        base_name = 'output'
        lily_file = TEMP_DIR.absolute() / f'{base_name}.ly'
        pdf_file = TEMP_DIR.absolute() / f'{base_name}.pdf'
        png_file = TEMP_DIR.absolute() / f'{base_name}.png'

        print(f"Processing file: {file.filename}")  # Debug log

        # Read content from uploaded file
        content = await file.read()
        content = content.decode('utf-8')

        # Create LilyPond file
        create_lily_file(content, lily_file, version)
        print(f"Created LilyPond file at: {lily_file}")  # Debug log

        # Check if lilypond is installed
        lilypond_check = subprocess.run(['which', 'lilypond'], capture_output=True, text=True)
        if lilypond_check.returncode != 0:
            raise Exception(f"LilyPond is not installed. Path check output: {lilypond_check.stderr}")

        # Run LilyPond with full error capture
        print("Running LilyPond...")  # Debug log
        process = subprocess.run(
            ['lilypond', '--pdf', '-o', str(TEMP_DIR.absolute() / base_name), str(lily_file)],
            capture_output=True,
            text=True
        )
        if process.returncode != 0:
            error_msg = f"LilyPond error:\nStdout: {process.stdout}\nStderr: {process.stderr}"
            print(error_msg)  # Debug log
            raise Exception(error_msg)

        # Check if ImageMagick is installed
        convert_check = subprocess.run(['which', 'convert'], capture_output=True, text=True)
        if convert_check.returncode != 0:
            raise Exception(f"ImageMagick is not installed. Path check output: {convert_check.stderr}")

        # Convert PDF to PNG with full error capture
        print("Converting PDF to PNG...")  # Debug log
        process = subprocess.run(
            ['convert', '-density', '300', str(pdf_file), str(png_file)],
            capture_output=True,
            text=True
        )
        if process.returncode != 0:
            error_msg = f"ImageMagick error:\nStdout: {process.stdout}\nStderr: {process.stderr}"
            print(error_msg)  # Debug log
            raise Exception(error_msg)

        # Verify files exist
        if not pdf_file.exists():
            raise Exception(f"PDF file was not created at {pdf_file}")
        if not png_file.exists():
            raise Exception(f"PNG file was not created at {png_file}")

        # Read the PNG file
        print("Reading PNG file...")  # Debug log
        with open(png_file, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')

        return LilyPondResponse(image=image_data)

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        error_details = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        print(f"Error occurred:\n{error_details}")  # Server log
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "traceback": error_details,
                "type": str(exc_type)
            }
        )

    finally:
        # Clean up temporary files
        for file in [lily_file, pdf_file, png_file]:
            if file and file.exists():
                try:
                    os.remove(file)
                    print(f"Cleaned up {file}")  # Debug log
                except Exception as e:
                    print(f"Error cleaning up {file}: {e}")  # Debug log

@app.post("/convert/binary", 
    response_model=LilyPondResponse,
    summary="Convert LilyPond text content to base64 image",
    description="Takes LilyPond notation as string and returns base64 encoded image")
async def convert_binary_to_image(data: BinaryInput):
    lily_file = None
    pdf_file = None
    png_file = None
    
    try:
        # Create temporary file paths
        TEMP_DIR.mkdir(exist_ok=True)
        
        base_name = 'output'
        lily_file = TEMP_DIR.absolute() / f'{base_name}.ly'
        pdf_file = TEMP_DIR.absolute() / f'{base_name}.pdf'
        png_file = TEMP_DIR.absolute() / f'{base_name}.png'

        print("Processing content")  # Debug log

        # Decode base64 content if it's base64 encoded
        try:
            content = base64.b64decode(data.content).decode('utf-8')
        except:
            content = data.content  # If not base64, use as is

        # Create LilyPond file
        create_lily_file(content, lily_file, data.version)
        print(f"Created LilyPond file at: {lily_file}")  # Debug log

        # Check if lilypond is installed
        lilypond_check = subprocess.run(['which', 'lilypond'], capture_output=True, text=True)
        if lilypond_check.returncode != 0:
            raise Exception(f"LilyPond is not installed. Path check output: {lilypond_check.stderr}")

        # Run LilyPond with full error capture
        print("Running LilyPond...")  # Debug log
        print(f"Current directory: {os.getcwd()}")  # Debug log
        print(f"File exists before LilyPond: {lily_file.exists()}")  # Debug log
        print(f"File contents:\n{lily_file.read_text()}")  # Debug log
        
        process = subprocess.run(
            ['lilypond',
             '--pdf',
             '-dbackend=eps',
             '-o', str(TEMP_DIR.absolute() / 'output'),
             str(lily_file.absolute())
            ],
            capture_output=True,
            text=True,
            cwd=str(TEMP_DIR.absolute())
        )
        
        if process.returncode != 0:
            error_msg = f"LilyPond error:\nStdout: {process.stdout}\nStderr: {process.stderr}"
            print(error_msg)  # Debug log
            raise Exception(error_msg)
            
        print(f"PDF exists after LilyPond: {pdf_file.exists()}")  # Debug log
        if pdf_file.exists():
            print(f"PDF size: {os.path.getsize(pdf_file)}")  # Debug log

        # Check if ImageMagick is installed
        convert_check = subprocess.run(['which', 'convert'], capture_output=True, text=True)
        if convert_check.returncode != 0:
            raise Exception(f"ImageMagick is not installed. Path check output: {convert_check.stderr}")

        # Convert PDF to PNG with full error capture
        print("Converting PDF to PNG...")  # Debug log
        process = subprocess.run(
            ['convert',
             '-density', '300',
             '-quality', '100',
             str(pdf_file.absolute()),
             str(png_file.absolute())
            ],
            capture_output=True,
            text=True
        )
        if process.returncode != 0:
            error_msg = f"ImageMagick error:\nStdout: {process.stdout}\nStderr: {process.stderr}"
            print(error_msg)  # Debug log
            raise Exception(error_msg)

        # Verify files exist
        if not pdf_file.exists():
            raise Exception(f"PDF file was not created at {pdf_file}")
        if not png_file.exists():
            raise Exception(f"PNG file was not created at {png_file}")

        # Read the PNG file
        print("Reading PNG file...")  # Debug log
        with open(png_file, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')

        return LilyPondResponse(image=image_data)

    except Exception as e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        error_details = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        print(f"Error occurred:\n{error_details}")  # Server log
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "traceback": error_details,
                "type": str(exc_type)
            }
        )

    finally:
        # Clean up temporary files
        for file in [lily_file, pdf_file, png_file]:
            if file and file.exists():
                try:
                    os.remove(file)
                    print(f"Cleaned up {file}")  # Debug log
                except Exception as e:
                    print(f"Error cleaning up {file}: {e}")  # Debug log

@app.on_event("startup")
async def startup_event():
    # Check for required dependencies
    dependencies = {
        'lilypond': 'Please install LilyPond: brew install lilypond',
        'convert': 'Please install ImageMagick: brew install imagemagick'
    }
    
    for cmd, msg in dependencies.items():
        if subprocess.run(['which', cmd], capture_output=True).returncode != 0:
            print(f"Warning: {msg}")

    # Create temp directory on startup
    temp_dir = Path('temp')
    temp_dir.mkdir(exist_ok=True) 