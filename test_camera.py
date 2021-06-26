import numpy as np
import cv2

# define the lower and upper boundaries of the colors in the HSV color space
lower = {'red':(0,80,80),
         'blue':(97,100,117),
         'black':(0,0,0),
         'white':(0,0,231)
         }

upper = {'red':(20,255,255),
         'blue':(117,255,255),
         'black':(50,50,100),
         'white':(180,18,255)
         }

# define standard colors for circle around the object
colors = {'red':(0,0,255),
          'blue':(255,0,0),
          'black':(0,0,0),
          'white':(255,255,255)
          }

font = cv2.FONT_HERSHEY_SIMPLEX

# Capturing video through webcam
webcam = cv2.VideoCapture(0)

while True:
    # grab the current frame
    #frame = cv2.imread('color.jpg')
    # Reading the video from the
    # webcam in image frames
    _, frame = webcam.read()

    blurred = cv2.GaussianBlur(frame,(11,11),0)
    hsv = cv2.cvtColor(blurred,cv2.COLOR_BGR2HSV)
    #for each color in dictionary check object in frame
    for key, value in upper.items():
        kernel = np.ones((9,9),np.uint8)
        mask = cv2.inRange(hsv,lower[key],upper[key])
        mask = cv2.morphologyEx(mask,cv2.MORPH_OPEN,kernel)
        mask = cv2.morphologyEx(mask,cv2.MORPH_CLOSE,kernel)

        #Calculate percentage of pixel colors
        output = cv2.countNonZero(mask)
        res = np.divide(float(output),mask.shape[0]*int(mask.shape[1] / 128))
        percent_colors = np.multiply((res),400) / 10000
        percent=(np.round(percent_colors*100,2))

        cnts = cv2.findContours(mask.copy(),cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)[-2]
        contours = cv2.findContours(mask.copy(),cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)[-2]
        center = None

        for contour in contours:
            cv2.drawContours(frame,[contour],0,(0,0,0),2)
            # get rotated rectangle from contour 
            rot_rect = cv2.minAreaRect(contour)
            box = cv2.boxPoints(rot_rect)
            box = np.int0(box)
            # draw rotated rectangle on copy of img
            cv2.drawContours(frame,[box],0,(0,0,0),2)
            
            print(colors[key])


        """
        if len(cnts) > 0:
            c = max(cnts, key=cv2.contourArea)
            ((x,y), radius) = cv2.minEnclosingCircle(c)
            M = cv2.moments(c)
            center = (int(M["m10"] / M["m00"]),int(M["m01"] / M["m00"]))

            if radius > 0.5:
                cv2.circle(frame,(int(x),int(y)),int(radius),colors[key],2)
                cv2.putText(frame,
                            str(percent) + '% ' +key,
                            (int(x-radius),int(y-radius)),
                            font,
                            0.6,
                            colors[key],
                            2)
        """
    # Program Termination
    cv2.imshow("Multiple Color square Detection in Real-TIme", frame)
    if cv2.waitKey(10) & 0xFF == ord('q'):
        cap.release()
        cv2.destroyAllWindows()
        break