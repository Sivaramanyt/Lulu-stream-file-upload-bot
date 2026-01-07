import requests
import config
import os
import tempfile
from typing import Optional, Dict

class LuluStreamClient:
    """Client for LuluStream API"""
    
    def __init__(self):
        self.api_key = config.LULUSTREAM_API_KEY
        self.upload_server = config.LULUSTREAM_UPLOAD_SERVER
        self.api_base = config.LULUSTREAM_API_BASE
    
    def get_upload_server(self) -> Optional[str]:
        """
        Get upload server URL
        GET https://lulustream.com/api/upload/server?key={api_key}
        """
        try:
            url = f"{self.api_base}/upload/server"
            params = {'key': self.api_key}
            
            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                if data.get('msg') == 'OK' and data.get('result'):
                    return data['result']
            
            print(f"[ERROR] Failed to get upload server: {response.text}")
            return None
        except Exception as e:
            print(f"[ERROR] Get upload server error: {e}")
            return None
    
    def upload_file(self, file_path: str, title: str = None, description: str = None, 
                   tags: str = None, snapshot_path: str = None) -> Optional[Dict]:
        """
        Upload file to LuluStream
        POST https://s1.myvideo.com/upload/01
        
        Returns:
            {"filecode": "xxx", "status": "OK"} on success
        """
        try:
            # Get upload server (optional, use default if fails)
            upload_url = self.get_upload_server() or self.upload_server
            
            print(f"[LULUSTREAM] Uploading to: {upload_url}")
            print(f"[LULUSTREAM] File: {file_path}")
            print(f"[LULUSTREAM] Title: {title}")
            
            # Prepare form data
            data = {
                'key': self.api_key,
                'fld_id': config.FOLDER_ID,
                'cat_id': config.CATEGORY_ID,
                'file_public': config.FILE_PUBLIC,
                'file_adult': config.FILE_ADULT,
            }
            
            # Add optional fields
            if title:
                data['file_title'] = title
            if description:
                data['file_descr'] = description
            if tags:
                data['tags'] = tags
            else:
                data['tags'] = config.DEFAULT_TAGS
            
            # Prepare files
            files = {
                'file': (os.path.basename(file_path), open(file_path, 'rb'), 'video/mp4')
            }
            
            # Add snapshot if provided
            if snapshot_path and os.path.exists(snapshot_path):
                files['snapshot'] = (os.path.basename(snapshot_path), open(snapshot_path, 'rb'), 'image/jpeg')
            
            # Upload with longer timeout for large files
            print(f"[LULUSTREAM] Starting upload...")
            response = requests.post(
                upload_url,
                data=data,
                files=files,
                timeout=7200  # 2 hour timeout for large files
            )
            
            # Close file handles
            for file_obj in files.values():
                if hasattr(file_obj[1], 'close'):
                    file_obj[1].close()
            
            print(f"[LULUSTREAM] Response status: {response.status_code}")
            print(f"[LULUSTREAM] Response: {response.text[:500]}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get('status') == 200 and data.get('result'):
                        filecode = data['result'][0].get('filecode')
                        if filecode:
                            return {
                                'success': True,
                                'filecode': filecode,
                                'url': f"https://luluvid.com/{filecode}"
                            }
                except ValueError:
                    pass
            
            return {
                'success': False,
                'error': f"Upload failed: {response.text[:200]}"
            }
            
        except Exception as e:
            print(f"[ERROR] LuluStream upload error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def upload_by_url(self, video_url: str, title: str = None, description: str = None,
                     tags: str = None) -> Optional[Dict]:
        """
        Upload video by URL - Direct to LuluStream API
        POST https://lulustream.com/api/upload/url
        
        Returns:
            {"filecode": "xxx", "status": 200} on success
        """
        try:
            # Build URL with API key as query parameter
            url = f"{self.api_base}/upload/url"
            
            # Prepare POST data with all parameters
            data = {
                'key': self.api_key,
                'url': video_url,
            }
            
            # Add optional parameters (use defaults if not provided)
            if config.FOLDER_ID:
                data['fld_id'] = config.FOLDER_ID
            if config.CATEGORY_ID:
                data['cat_id'] = config.CATEGORY_ID
            
            data['file_public'] = config.FILE_PUBLIC if hasattr(config, 'FILE_PUBLIC') else '1'
            data['file_adult'] = config.FILE_ADULT if hasattr(config, 'FILE_ADULT') else '0'
            
            if title:
                data['file_title'] = title
            if description:
                data['file_descr'] = description
            if tags:
                data['tags'] = tags
            elif hasattr(config, 'DEFAULT_TAGS'):
                data['tags'] = config.DEFAULT_TAGS
            
            print(f"[LULUSTREAM] === URL UPLOAD REQUEST ===")
            print(f"[LULUSTREAM] URL: {video_url}")
            print(f"[LULUSTREAM] Title: {title}")
            print(f"[LULUSTREAM] API Endpoint: {url}")
            print(f"[LULUSTREAM] API Key: {self.api_key[:12]}...")
            print(f"[LULUSTREAM] Folder ID: {config.FOLDER_ID if hasattr(config, 'FOLDER_ID') else 'None'}")
            print(f"[LULUSTREAM] Data: {data}")
            
            # Make request with headers similar to browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Accept-Language': 'en-US,en;q=0.9',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            }
            
            response = requests.post(url, data=data, headers=headers, timeout=120)
            
            print(f"[LULUSTREAM] === URL UPLOAD RESPONSE ===")
            print(f"[LULUSTREAM] Status Code: {response.status_code}")
            print(f"[LULUSTREAM] Response Headers: {dict(response.headers)}")
            print(f"[LULUSTREAM] Response Body: {response.text}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"[LULUSTREAM] Parsed JSON: {result}")
                    
                    # Check various response formats
                    if result.get('status') == 200:
                        # Response format 1: {"status": 200, "result": {"filecode": "xxx"}}
                        if result.get('result'):
                            filecode = result['result'].get('filecode')
                            if filecode:
                                print(f"[LULUSTREAM] ✅ SUCCESS - Filecode: {filecode}")
                                return {
                                    'success': True,
                                    'filecode': filecode,
                                    'url': f"https://luluvid.com/{filecode}"
                                }
                    
                    # Response format 2: {"msg": "OK", "result": {"filecode": "xxx"}}
                    elif result.get('msg') == 'OK' and result.get('result'):
                        filecode = result['result'].get('filecode')
                        if filecode:
                            print(f"[LULUSTREAM] ✅ SUCCESS - Filecode: {filecode}")
                            return {
                                'success': True,
                                'filecode': filecode,
                                'url': f"https://luluvid.com/{filecode}"
                            }
                    
                    # Check if there's an error message
                    error_msg = result.get('msg') or result.get('error') or result.get('message')
                    if error_msg:
                        print(f"[LULUSTREAM] ❌ API Error: {error_msg}")
                        return {
                            'success': False,
                            'error': f"LuluStream API error: {error_msg}"
                        }
                    
                except ValueError as e:
                    print(f"[LULUSTREAM] ❌ JSON Parse Error: {e}")
                    pass
            
            # If we got here, something went wrong
            error_text = response.text[:500] if len(response.text) > 500 else response.text
            print(f"[LULUSTREAM] ❌ Upload failed: {error_text}")
            
            return {
                'success': False,
                'error': f"URL upload failed (Status {response.status_code}): {error_text}"
            }
            
        except Exception as e:
            print(f"[LULUSTREAM] ❌ EXCEPTION: {e}")
            import traceback
            print(f"[LULUSTREAM] Traceback: {traceback.format_exc()}")
            return {
                'success': False,
                'error': f"Exception: {str(e)}"
            }
    
    def get_file_info(self, filecode: str) -> Optional[Dict]:
        """
        Get file information
        GET https://lulustream.com/api/file/info?key={api_key}&file_code={filecode}
        """
        try:
            url = f"{self.api_base}/file/info"
            params = {
                'key': self.api_key,
                'file_code': filecode
            }
            
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            
            return None
        except Exception as e:
            print(f"[ERROR] Get file info error: {e}")
            return None
    
    def get_encoding_status(self, filecode: str) -> Optional[Dict]:
        """
        Get encoding status
        GET https://lulustream.com/api/file/encodings?key={api_key}&file_code={filecode}
        """
        try:
            url = f"{self.api_base}/file/encodings"
            params = {
                'key': self.api_key,
                'file_code': filecode
            }
            
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            
            return None
        except Exception as e:
            print(f"[ERROR] Get encoding status error: {e}")
            return None
