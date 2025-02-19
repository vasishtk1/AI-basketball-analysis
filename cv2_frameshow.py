# importing the necessary libraries
import cv2
import numpy as np
import matplotlib.pyplot as plt
import scipy.optimize as opt
import tensorflow.compat.v1 as tf
tf.disable_v2_behavior()
import pickle
import os
import sys
from sys import platform
# from google.colab.patches import cv2_imshow as cv2
def tensorflow_init():
    MODEL_NAME = 'inference_graph'
    PATH_TO_CKPT = MODEL_NAME + '/frozen_inference_graph.pb'

    detection_graph = tf.Graph()
    with detection_graph.as_default():
        od_graph_def = tf.GraphDef()
        with tf.gfile.GFile(PATH_TO_CKPT, 'rb') as fid:
            serialized_graph = fid.read()
            od_graph_def.ParseFromString(serialized_graph)
            tf.import_graph_def(od_graph_def, name='')

    image_tensor = detection_graph.get_tensor_by_name('image_tensor:0')
    boxes = detection_graph.get_tensor_by_name('detection_boxes:0')
    scores = detection_graph.get_tensor_by_name('detection_scores:0')
    classes = detection_graph.get_tensor_by_name('detection_classes:0')
    num_detections = detection_graph.get_tensor_by_name('num_detections:0')
    return detection_graph, image_tensor, boxes, scores, classes, num_detections

def openpose_init():
    try:
        if platform == "win32":
            sys.path.append(os.path.dirname(os.getcwd()))
            import OpenPose.Release.pyopenpose as op
        else:
            path = os.path.join(os.getcwd(), 'OpenPose/openpose')
            # print(path)
            sys.path.append(path)
            import pyopenpose as op
    except ImportError as e:
        # print("Something went wrong when importing OpenPose")
        raise e

    # Custom Params (refer to include/openpose/flags.hpp for more parameters)
    params = dict()
    params["model_folder"] = "./OpenPose/models"

    # Starting OpenPose
    opWrapper = op.WrapperPython()
    opWrapper.configure(params)
    opWrapper.start()

    # Process Image
    datum = op.Datum()
    return datum, opWrapper


def detect_image(img):
    # obtains height and width of the image
    height, width = img.shape[:2]
    # initializes tensorflow 
    detection_graph, image_tensor, boxes, scores, classes, num_detections = tensorflow_init()
    # initiates tensorflow session
    with tf.Session(graph=detection_graph) as sess:
        # gets the expanded array
        img_expanded = np.expand_dims(img, axis=0)
        # creates a default graph 
        (boxes, scores, classes, num_detections) = sess.run(
            [boxes, scores, classes, num_detections],
            feed_dict={image_tensor: img_expanded})
        valid_detections = 0

        xCoor = -1
        yCoor = -1
        for i, box in enumerate(boxes[0]):
            # print("detect")
            if (scores[0][i] > 0.5):
                valid_detections += 1
                ymin = int((box[0] * height))
                xmin = int((box[1] * width))
                ymax = int((box[2] * height))
                xmax = int((box[3] * width))
                xCoor = int(np.mean([xmin, xmax]))
                yCoor = int(np.mean([ymin, ymax]))
                # if it finds the basketball, it draws a cirlce around it
                if(classes[0][i] == 1):  # basketball
                    cv2.circle(img=img, center=(xCoor, yCoor), radius=25,
                               color=(255, 0, 0), thickness=-1)
                    cv2.putText(img, "BALL", (xCoor - 50, yCoor - 50),
                                cv2.FONT_HERSHEY_COMPLEX, 3, (255, 0, 0), 8)
                    # print("add basketball")
            
    return xCoor, yCoor

def calculateAngle(a, b, c):
    ba = a - b
    bc = c - b
    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
    angle = np.arccos(cosine_angle)
    return round(np.degrees(angle), 2)

def detect_shot(frame, trace, width, height, previous, during_shooting, shot_result, fig, datum, opWrapper, shooting_pose):
    global shooting_result

    if(shot_result['displayFrames'] > 0):
        shot_result['displayFrames'] -= 1
    if(shot_result['release_displayFrames'] > 0):
        shot_result['release_displayFrames'] -= 1
    if(shooting_pose['ball_in_hand']):
        shooting_pose['ballInHand_frames'] += 1
        # print("ball in hand")

    count = 0
    # Loop until the end of the frame
    detection_graph, image_tensor, boxes, scores, classes, num_detections = tensorflow_init()
    with tf.Session(graph=detection_graph) as sess:
        # gets the expanded array
        frame_expanded = np.expand_dims(frame, axis=0)
        valid_detections = 0
        # main tensorflow detection
        (boxes, scores, classes, num_detections) = sess.run(
            [boxes, scores, classes, num_detections],
            feed_dict={image_tensor: frame_expanded})
        xCoor = -1
        yCoor = -1
        for i, box in enumerate(boxes[0]):
            if (scores[0][i] > 0.5):
                ymin = int((box[0] * height))
                xmin = int((box[1] * width))
                ymax = int((box[2] * height))
                xmax = int((box[3] * width))
                xCoor = int(np.mean([xmin, xmax]))
                yCoor = int(np.mean([ymin, ymax]))
                if(classes[0][i] == 2):  # Rim
                    # cover previous hoop with white rectangle
                    cv2.rectangle(
                        trace, (previous['hoop'][0], previous['hoop'][1]), (previous['hoop'][2], previous['hoop'][3]), (255, 255, 255), 5)
                    cv2.rectangle(frame, (xmin, ymax),
                                (xmax, ymin), (48, 124, 255), 5)
                    cv2.rectangle(trace, (xmin, ymax),
                                (xmax, ymin), (48, 124, 255), 5)

                    #display judgement after shot
                    if(shot_result['displayFrames']):
                        if(shot_result['judgement'] == "MISS"):
                            cv2.putText(frame, shot_result['judgement'], (xCoor - 65, yCoor - 65),
                                        cv2.FONT_HERSHEY_COMPLEX, 3, (0, 0, 255), 8)
                        else:
                            cv2.putText(frame, shot_result['judgement'], (xCoor - 65, yCoor - 65),
                                        cv2.FONT_HERSHEY_COMPLEX, 3, (82, 168, 50), 8)
                    cv2.imshow('window-name', frame)
                    cv2.imwrite("rim_frame%d.jpg" % count, frame)
                    count = count + 1

                    if cv2.waitKey(10) & 0xFF == ord('q'):
                        break
                    previous['hoop'][0] = xmin
                    previous['hoop'][1] = ymax
                    previous['hoop'][2] = xmax
                    previous['hoop'][3] = ymin
                    previous['hoop_height'] = max(ymin, previous['hoop_height'])
                    xRect = (xmin, xmax)
                    yRect = (ymin, ymax)
    return [xRect, yRect]

                    

def detect_image_wrapper(video_name):
    count = 0
    ball_position_coordinates = []
    cap = cv2.VideoCapture(video_name)
    # Loop until the end of the video
    while (cap.isOpened()):
    
        # Capture frame-by-frame
        ret, frame = cap.read()
        if not ret:
            break
        # frame = cv2.resize(frame, (540, 380), fx = 0, fy = 0,
                            # interpolation = cv2.INTER_CUBIC)
    
        # Display the resulting frame
        # cv2.imshow('Frame', frame)
        
        ret,frame = cap.read()
        xCoor, yCoor = detect_image(frame)
        ball_position_coordinates.append([xCoor, yCoor])
        cv2.imshow('window-name', frame)
        cv2.imwrite("frame%d.jpg" % count, frame)
        count = count + 1
        if cv2.waitKey(10) & 0xFF == ord('q'):
            break

    print(ball_position_coordinates)
    with open(video_name + '.pkl', 'wb') as f:
        pickle.dump(ball_position_coordinates, f)
    with open(video_name + '.txt', 'w') as f:
        for listitem in ball_position_coordinates:
            f.write("\n" + repr(listitem))
    # release the video capture object
    cap.release()
    # Closes all the windows currently opened.
    cv2.destroyAllWindows()

    return ball_position_coordinates

def detect_shot_wrapper(video_name):
    # print("Starting the function")
    # datum, opWrapper = openpose_init()

    # frame, trace, width, height, sess, image_tensor, boxes, scores, classes, num_detections, previous, during_shooting, shot_result, fig, datum, opWrapper, shooting_pose
    # Creating a VideoCapture object to read the video
    cap = cv2.VideoCapture(video_name)
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    fps = cap.get(cv2.CAP_PROP_FPS)
    trace = np.full((int(height), int(width), 3), 255, np.uint8)
    #objects to store detection status
    previous = {
        'ball': np.array([0, 0]),  # x, y
        'hoop': np.array([0, 0, 0, 0]),  # xmin, ymax, xmax, ymin
            'hoop_height': 0
        }
    during_shooting = {
            'isShooting': False,
            'balls_during_shooting': [],
            'release_angle_list': [],
            'release_point': []
        }
    shooting_pose = {
            'ball_in_hand': False,
            'elbow_angle': 370,
            'knee_angle': 370,
            'ballInHand_frames': 0,
            'elbow_angle_list': [],
            'knee_angle_list': [],
            'ballInHand_frames_list': []
        }
    shot_result = {
            'displayFrames': 0,
            'release_displayFrames': 0,
            'judgement': ""
        }
    count = 0
    rim_position_coordinates = []
    while (cap.isOpened()):
    
        # Capture frame-by-frame
        ret, frame = cap.read()
        if not ret:
            break
        # frame = cv2.resize(frame, (540, 380), fx = 0, fy = 0,
                            # interpolation = cv2.INTER_CUBIC)
    
        # Display the resulting frame
        # cv2.imshow('Frame', frame)
        
        ret,frame = cap.read()
        rim_position = detect_shot(frame, trace, width, height, previous, during_shooting, shot_result, 0, 0, 0, shooting_pose)
        rim_position_coordinates.append(rim_position)

    print(rim_position_coordinates)
    print(len(rim_position_coordinates))

    # release the video capture object
    cap.release()
    # Closes all the windows currently opened.
    cv2.destroyAllWindows()

# This is the function we are trying to fit to the data.
def fit_func_1(x,a,b,c,d):
  return a*(x-b)**2+c+d*0.0001*np.cos(x)

def fit_func_2(x,a,b,c):
  return a*(x-b)**2+c



#invoking image detection 
#video_name = 'screenshot.png'
# video_name = 'IMG_1266.mp4'
video_name = 'IMG_0369.mp4'

"""
detect_shot_wrapper(video_name)
"""

print("read video_name")
ball_position_coordinates = detect_image_wrapper(video_name)
print("detect_image_wrapper completed")

trajectory_x = []
trajectory_y = []
# sample list of ball coordinates - IMG_0369.mp4
# ball_position_coordinates = [[474, 787], [468, 735], [461, 814], [456, 641], [459, 626], [466, 614], [473, 605], [483, 605], [492, 611], [497, 622], [499, 629], [504, 634], [508, 636], [516, 641], [533, 648], [539, 642], [563, 618], [575, 581], [1406, 275], [540, 505], [450, 477], [448, 459], [554, 348], [613, 271], [459, 433], [729, 144], [785, 97], [456, 486], [450, 486], [949, 22], [999, 19], [1043, 26], [1090, 26], [439, 485], [436, 484], [434, 486], [436, 487], [440, 487], [1345, 241], [1358, 313], [1373, 310], [1367, 307], [452, 488], [456, 493], [469, 491], [476, 491], [1341, 400], [1347, 317], [1348, 317], [1348, 313], [1301, 609], [1288, 675], [1285, 752], [1277, 793], [1268, 732], [1350, 310], [1351, 306], [1350, 305], [1351, 307], [1231, 526], [1225, 513], [1220, 505], [1216, 500]]

# sample list of rim coordinates - IMG_0369.mp4
# rim_position_coordinates = [[(1377, 1482), (204, 300)], [(1375, 1480), (204, 302)], [(1376, 1478), (204, 301)], [(1374, 1475), (204, 300)], [(1372, 1476), (204, 304)], [(1370, 1476), (205, 306)], [(1369, 1475), (207, 307)], [(1369, 1476), (207, 311)], [(1369, 1475), (208, 313)], [(1370, 1475), (207, 316)], [(1370, 1476), (211, 311)], [(1368, 1476), (212, 311)], [(1366, 1475), (212, 318)], [(1362, 1475), (214, 320)], [(1357, 1473), (216, 319)], [(1357, 1469), (220, 318)], [(1357, 1467), (220, 319)], [(1355, 1462), (222, 319)], [(1355, 1458), (226, 324)], [(1353, 1458), (230, 326)], [(1350, 1455), (232, 324)], [(1347, 1452), (235, 331)], [(1347, 1449), (234, 333)], [(1344, 1444), (237, 329)], [(1341, 1447), (238, 334)], [(1338, 1443), (241, 340)], [(1335, 1444), (246, 346)], [(1331, 1443), (245, 346)], [(1330, 1437), (247, 348)], [(1327, 1431), (251, 351)], [(1326, 1429), (253, 351)], [(1324, 1425), (255, 348)], [(1323, 1423), (258, 352)], [(1317, 1420), (260, 356)], [(1315, 1417), (259, 356)], [(1313, 1412), (262, 356)], [(1310, 1414), (263, 355)], [(1310, 1408), (263, 355)], [(1311, 1405), (273, 357)], [(1305, 1411), (266, 360)], [(1315, 1432), (270, 351)], [(1306, 1428), (268, 346)], [(1304, 1419), (265, 349)], [(1312, 1414), (268, 351)], [(1305, 1406), (263, 357)], [(1298, 1401), (265, 373)], [(1298, 1399), (268, 370)], [(1299, 1396), (268, 367)], [(1300, 1396), (268, 366)], [(1299, 1398), (264, 362)], [(1298, 1398), (264, 359)], [(1297, 1398), (263, 363)], [(1299, 1400), (263, 364)], [(1299, 1400), (261, 359)], [(1298, 1400), (258, 358)], [(1298, 1402), (259, 361)], [(1300, 1403), (258, 354)], [(1299, 1401), (258, 353)], [(1297, 1405), (258, 357)], [(1297, 1405), (255, 355)], [(1298, 1403), (252, 356)], [(1299, 1404), (250, 357)], [(1301, 1405), (248, 353)]]

"""
for listitem in ball_position_coordinates[1:]:
    x = -listitem[1]
    y = listitem[0]
    trajectory_x.append(x)
    trajectory_y.append(y)

plt.scatter(trajectory_y, trajectory_x)

"""

"""
#using our curve_fit() function using fit_func_1
popt, pcov = opt.curve_fit(fit_func_1,trajectory_y,trajectory_x,p0=[1,2,-16,1])

a_opt, b_opt, c_opt, d_opt = popt
x_model = np.linspace(min(trajectory_y), max(trajectory_x))
y_model = fit_func_1(x_model, a_opt, b_opt, c_opt,d_opt) 
plt.plot(x_model, y_model, color='r')

#using our curve_fit() function using fit_func_2
popt, pcov = opt.curve_fit(fit_func_2,trajectory_y,trajectory_x,p0=[3,2,-16])

a_opt, b_opt, c_opt = popt
x_model = np.linspace(min(trajectory_y), max(trajectory_x))
y_model = fit_func_2(x_model, a_opt, b_opt, c_opt) 
plt.plot(x_model, y_model, color='b')

#fit fourth-degree polynomial
# model4 = np.poly1d(np.polyfit(df.x, df.y, 4))

#add fitted polynomial curve to scatterplot
# plt.plot(polyline, model4(polyline), '--', color='red')

"""

"""
plt.xlabel('X-coordinate')
plt.ylabel('Y-coordinate')
plt.title('Basketball Trajectory')
plt.show()

"""


# CMake installations
# https://medium.com/@alok.gandhi2002/build-openpose-with-without-gpu-support-for-macos-catalina-10-15-6-8fb936c9ab05
# https://maelfabien.github.io/tutorials/open-pose/#installation

# under openpose git repo
# protoc ./3rdparty/caffe/src/caffe/proto/caffe.proto --cpp_out=.
# mkdir ./3rdparty/caffe/include/caffe/proto
# mv ./3rdparty/caffe/src/caffe/proto/caffe.pb.h ./3rdparty/caffe/include/caffe/proto

# protoc --proto_path=[full path where exist file[ProtobufTypes.proto] --cpp_out=[full path where exist file[ProtobufTypes.proto] [full path where exist file[ProtobufTypes.proto]/ProtobufTypes.proto
