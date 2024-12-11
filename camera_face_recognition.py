import cv2
import face_recognition
import os
import time
import numpy as np
import mediapipe as mp

KNOWN_FACES_DIR = "./assets/known_faces"
CONFIDENCE_THRESHOLD = 0.6  # The threshold to filter out low-confidence matches
max_wait_time = 10
max_no_face_time = 30  # Maximum time (seconds) without a known face to exit

known_face_encodings = []
known_face_names = []

def load_known_faces(directory):
    global known_face_encodings, known_face_names
    known_face_encodings = []
    known_face_names = []
    for filename in os.listdir(directory):
        if filename.endswith(".jpg") or filename.endswith(".png") or filename.endswith(".jpeg"):
            image_path = os.path.join(directory, filename)
            image = face_recognition.load_image_file(image_path)
            face_encoding = face_recognition.face_encodings(image)
            if face_encoding:
                known_face_encodings.append(face_encoding[0])
                known_face_names.append(os.path.splitext(filename)[0])

# Initialize MediaPipe Face Detection
mp_face_detection = mp.solutions.face_detection
mp_drawing = mp.solutions.drawing_utils

cap = cv2.VideoCapture(0)

load_known_faces(KNOWN_FACES_DIR)

known_face_seen_time = None
no_face_detected_time = None

face_locations = []
face_encodings = []
face_names = []

with mp_face_detection.FaceDetection(min_detection_confidence=0.2) as face_detection:
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces using MediaPipe
        results = face_detection.process(rgb_frame)

        face_detected = False  # Flag to track if any known face is detected
        recognized_faces = set()  # Set to store recognized faces in the current frame

        # If faces are detected by MediaPipe
        if results.detections:
            for detection in results.detections:
                # Get bounding box coordinates from MediaPipe
                bboxC = detection.location_data.relative_bounding_box
                ih, iw, _ = frame.shape
                top_left = (int(bboxC.xmin * iw), int(bboxC.ymin * ih))
                bottom_right = (int((bboxC.xmin + bboxC.width) * iw), int((bboxC.ymin + bboxC.height) * ih))

                # Extract the face region
                face_region = frame[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]]
                rgb_face_region = cv2.cvtColor(face_region, cv2.COLOR_BGR2RGB)

                # Get face encoding using face_recognition
                face_encoding = face_recognition.face_encodings(rgb_face_region)

                if face_encoding:
                    face_encoding = face_encoding[0]
                    matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
                    face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)

                    # Only consider a match if the face distance is lower than a threshold
                    best_match_index = np.argmin(face_distances)
                    best_match_distance = face_distances[best_match_index]

                    if matches[best_match_index] and best_match_distance <= CONFIDENCE_THRESHOLD:
                        name = known_face_names[best_match_index]
                        color = (0, 255, 0)  # Green for recognized face
                        face_detected = True

                        # If the face has not been recognized already in this frame, process it
                        if name not in recognized_faces:
                            recognized_faces.add(name)  # Add name to recognized faces for this frame
                            
                            # Update the timer if a known face is detected
                            if known_face_seen_time is None:
                                known_face_seen_time = time.time()
                            
                            time_elapsed = time.time() - known_face_seen_time
                            time_remaining = max_wait_time - int(time_elapsed)
                            
                            # If time is up, exit
                            if time_remaining <= 0:
                                try:
                                    cap.release()
                                    cv2.destroyAllWindows()
                                    break 
                                except Exception as e:
                                    print(f"Error closing video: {e}")
                    else:
                        name = "Unknown"
                        color = (0, 0, 255)  # Red for unknown face
                        known_face_seen_time = None
                        time_remaining = 0
                    
                    # Draw the rectangle and label with confidence
                    cv2.rectangle(frame, top_left, bottom_right, color, 2)
                    font = cv2.FONT_HERSHEY_DUPLEX
                    cv2.putText(frame, name, (top_left[0] + 6, bottom_right[1] - 6), font, 0.5, color, 1)

                    if known_face_seen_time is not None:
                        cv2.putText(frame, f"Time remaining: {time_remaining}s", (10, 30), font, 1, (255, 255, 255), 2)
        
        if not face_detected:
            if no_face_detected_time is None:
                no_face_detected_time = time.time()  
            else:
                time_without_face = time.time() - no_face_detected_time
                if time_without_face >= max_no_face_time:
                    print("No known face detected for 30 seconds. Returning to login.")
                    cap.release()
                    cv2.destroyAllWindows()
                    break
        else:
            no_face_detected_time = None 
        
        # Reset the recognized faces at the end of each frame
        recognized_faces.clear()
        
        cv2.imshow("Face Recognition", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
