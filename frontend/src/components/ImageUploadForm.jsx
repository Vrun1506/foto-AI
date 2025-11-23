import React, { useState } from 'react';
import { Upload, X } from 'lucide-react';

export default function ImageUploadForm() {
  const [image, setImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [text, setText] = useState('');
  const [isDragging, setIsDragging] = useState(false);

  const handleImageChange = (file) => {
    if (file && file.type.startsWith('image/')) {
      setImage(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setImagePreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleFileInput = (e) => {
    const file = e.target.files[0];
    handleImageChange(file);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    handleImageChange(file);
  };

  const removeImage = () => {
    setImage(null);
    setImagePreview(null);
  };

  const handleSubmit = () => {
    console.log('Submitted:', { image, text });
    alert('Form submitted! Check console for details.');
  };

  return (
    <>
      <style>{`
        * {
          margin: 0;
          padding: 0;
          box-sizing: border-box;
        }

        body {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
        }

        .container {
          min-height: 100vh;
          background: linear-gradient(135deg, #EBF4FF 0%, #E0E7FF 100%);
          padding: 48px 16px;
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
        }

        .content-wrapper {
          max-width: 768px;
          margin: 0 auto;
        }

        .logo-section {
          text-align: center;
          margin-bottom: 32px;
        }

        .logo-circle {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 80px;
          height: 80px;
          background-color: #4F46E5;
          border-radius: 50%;
          margin-bottom: 16px;
        }

        .logo-icon {
          width: 40px;
          height: 40px;
          color: white;
        }

        .title {
          font-size: 30px;
          font-weight: bold;
          color: #1F2937;
        }

        .form-container {
          background: white;
          border-radius: 16px;
          box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
          padding: 32px;
        }

        .form-section {
          margin-bottom: 24px;
        }

        .label {
          display: block;
          font-size: 14px;
          font-weight: 500;
          color: #374151;
          margin-bottom: 8px;
        }

        .upload-area {
          border: 2px dashed #D1D5DB;
          border-radius: 8px;
          padding: 32px;
          text-align: center;
          transition: all 0.2s;
          cursor: pointer;
        }

        .upload-area:hover {
          border-color: #818CF8;
        }

        .upload-area.dragging {
          border-color: #4F46E5;
          background-color: #EEF2FF;
        }

        .upload-icon {
          width: 48px;
          height: 48px;
          color: #9CA3AF;
          margin: 0 auto 16px;
        }

        .upload-text {
          color: #4B5563;
          margin-bottom: 8px;
        }

        .browse-button {
          display: inline-block;
          padding: 8px 16px;
          background-color: #4F46E5;
          color: white;
          border-radius: 8px;
          cursor: pointer;
          transition: background-color 0.2s;
        }

        .browse-button:hover {
          background-color: #4338CA;
        }

        .file-input {
          display: none;
        }

        .upload-hint {
          font-size: 14px;
          color: #6B7280;
          margin-top: 8px;
        }

        .image-preview-container {
          position: relative;
        }

        .image-preview {
          width: 100%;
          height: 256px;
          object-fit: cover;
          border-radius: 8px;
        }

        .remove-button {
          position: absolute;
          top: 8px;
          right: 8px;
          padding: 8px;
          background-color: #EF4444;
          color: white;
          border: none;
          border-radius: 50%;
          cursor: pointer;
          transition: background-color 0.2s;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .remove-button:hover {
          background-color: #DC2626;
        }

        .remove-icon {
          width: 20px;
          height: 20px;
        }

        .textarea {
          width: 100%;
          padding: 12px 16px;
          border: 1px solid #D1D5DB;
          border-radius: 8px;
          font-size: 14px;
          font-family: inherit;
          resize: none;
          transition: all 0.2s;
        }

        .textarea:focus {
          outline: none;
          border-color: #4F46E5;
          box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
        }

        .submit-button {
          width: 100%;
          padding: 12px;
          background-color: #4F46E5;
          color: white;
          border: none;
          border-radius: 8px;
          font-size: 16px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }

        .submit-button:hover {
          background-color: #4338CA;
          box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        }
      `}</style>

      <div className="container">
        <div className="content-wrapper">
          {/* Logo */}
          <div className="logo-section">
            <div className="logo-circle">
              <Upload className="logo-icon" />
            </div>
            <h1 className="title">Upload & Share</h1>
          </div>

          {/* Main Container */}
          <div className="form-container">
            {/* Image Upload Section */}
            <div className="form-section">
              <label className="label">Upload Image</label>
              
              {!imagePreview ? (
                <div
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  className={`upload-area ${isDragging ? 'dragging' : ''}`}
                >
                  <Upload className="upload-icon" />
                  <p className="upload-text">
                    Drag and drop your image here, or
                  </p>
                  <label className="browse-button">
                    Browse Files
                    <input
                      type="file"
                      accept="image/*"
                      onChange={handleFileInput}
                      className="file-input"
                    />
                  </label>
                  <p className="upload-hint">
                    PNG, JPG, GIF up to 10MB
                  </p>
                </div>
              ) : (
                <div className="image-preview-container">
                  <img
                    src={imagePreview}
                    alt="Preview"
                    className="image-preview"
                  />
                  <button
                    type="button"
                    onClick={removeImage}
                    className="remove-button"
                  >
                    <X className="remove-icon" />
                  </button>
                </div>
              )}
            </div>

            {/* Text Input Section */}
            <div className="form-section">
              <label className="label">Enter prompt details...</label>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Example: Can you decrease the expoures and saturation on this photo by 50%?"
                rows="4"
                className="textarea"
              />
            </div>

            {/* Submit Button */}
            <button
              onClick={handleSubmit}
              className="submit-button"
            >
              Submit
            </button>
          </div>
        </div>
      </div>
    </>
  );
}