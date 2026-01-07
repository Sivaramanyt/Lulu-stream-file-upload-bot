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
        Upload video by URL
        POST https://lulustream.com/api/upload/url?key={api_key}
        
        Returns:
            {"filecode": "xxx", "status": "OK"} on success
        """
        try:
            # Build URL with API key as query parameter
            url = f"{self.api_base}/upload/url?key={self.api_key}"
            
            # Prepare POST data (without key, as it's in URL)
            data = {
                'url': video_url,
                'fld_id': config.FOLDER_ID,
                'cat_id': config.CATEGORY_ID,
                'file_public': config.FILE_PUBLIC,
                'file_adult': config.FILE_ADULT,
            }
            
            if title:
                data['file_title'] = title
            if description:
                data['file_descr'] = description
            if tags:
                data['tags'] = tags
            else:
                data['tags'] = config.DEFAULT_TAGS
            
            print(f"[LULUSTREAM] Uploading by URL: {video_url}")
            print(f"[LULUSTREAM] API Key: {self.api_key[:8]}...")
            
            response = requests.post(url, data=data, timeout=60)
            
            print(f"[LULUSTREAM] Response status: {response.status_code}")
            print(f"[LULUSTREAM] Response: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 200 and result.get('result'):
                    filecode = result['result'].get('filecode')
                    if filecode:
                        return {
                            'success': True,
                            'filecode': filecode,
                            'url': f"https://luluvid.com/{filecode}"
                        }
            
            return {
                'success': False,
                'error': f"URL upload failed: {response.text[:200]}"
            }
            
        except Exception as e:
            print(f"[ERROR] LuluStream URL upload error: {e}")
            return {
                'success': False,
                'error': str(e)
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
