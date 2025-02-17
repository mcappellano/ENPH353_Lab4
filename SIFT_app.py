#!/usr/bin/env python3

from PyQt5 import QtCore, QtGui, QtWidgets
from python_qt_binding import loadUi

import cv2
import sys
import numpy as np

class My_App(QtWidgets.QMainWindow):

    def __init__(self):
        super(My_App, self).__init__()
        loadUi("./SIFT_app.ui", self)

        self._cam_id = 0
        self._cam_fps = 20
        self._is_cam_enabled = False
        self._is_template_loaded = False

        self.browse_button.clicked.connect(self.SLOT_browse_button)
        self.toggle_cam_button.clicked.connect(self.SLOT_toggle_camera)

        self._camera_device = cv2.VideoCapture(self._cam_id)
        self._camera_device.set(3, 320)
        self._camera_device.set(4, 240)

        # Timer used to trigger the camera
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self.SLOT_query_camera)
        self._timer.setInterval(1000 / self._cam_fps)


    def SLOT_browse_button(self):
        dlg = QtWidgets.QFileDialog()
        dlg.setFileMode(QtWidgets.QFileDialog.ExistingFile)
        if dlg.exec_():
            self.template_path = dlg.selectedFiles()[0]

        pixmap = QtGui.QPixmap(self.template_path)
        self.template_label.setPixmap(pixmap)
        print("Loaded template image file: " + self.template_path)

    # Source: stackoverflow.com/questions/34232632/
    def convert_cv_to_pixmap(self, cv_img):
        cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        height, width, channel = cv_img.shape
        bytesPerLine = channel * width
        q_img = QtGui.QImage(cv_img.data, width, height, 
                             bytesPerLine, QtGui.QImage.Format_RGB888)
        return QtGui.QPixmap.fromImage(q_img)

    def SLOT_query_camera(self):
        img = cv2.imread(self.template_path,cv2.IMREAD_GRAYSCALE) #query image

        #Features
        sift = cv2.SIFT_create()
        kp_image, desc_image = sift.detectAndCompute(img, None)
        #img = cv2.drawKeypoints(img, kp_image, img)

        #Feature matching
        index_params = dict(algorithm = 0, trees = 5)
        search_params = dict()
        flann = cv2.FlannBasedMatcher(index_params, search_params)

        while True:
            ret, frame = self._camera_device.read()

            grayframe = cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY) #trainimage
            kp_grayframe, desc_grayframe = sift.detectAndCompute(grayframe, None)
            #grayframe = cv2.drawKeypoints(grayframe, kp_grayframe, grayframe)

            matches = flann.knnMatch(desc_image, desc_grayframe, k = 2)

            good_points = []
            for m,n in matches:
                if m.distance < 0.6* n.distance:
                    good_points.append(m)

            #img3 = cv2.drawMatches(img, kp_image,grayframe,kp_grayframe,good_points, grayframe)

            # Homography
            if len(good_points) > 10:
                query_pts = np.float32([kp_image[m.queryIdx].pt for m in good_points]).reshape(-1,1,2)
                train_pts = np.float32([kp_grayframe[m.trainIdx].pt for m in good_points]).reshape(-1,1,2)

                matrix, mask = cv2.findHomography(query_pts, train_pts, cv2.RANSAC, 5.0)
                matches_mask = mask.ravel().tolist()

                #Perspective transform
                h, w = img.shape
                pts = np.float32([[0,0],[0,h],[w,h],[w,0]]).reshape(-1,1,2)
                dst = cv2.perspectiveTransform(pts,matrix)

                homography = cv2.polylines(frame, [np.int32(dst)], True, (255,0 ,0), 3)

                cv2.imshow("Homography", homography)
                
                # pixmap = self.convert_cv_to_pixmap(homography)
                # self.live_image_label.setPixmap(pixmap)

            else:

                # pixmap = self.convert_cv_to_pixmap(grayframe)
                # self.live_image_label.setPixmap(pixmap)

                cv2.imshow("Homography", grayframe)


            #cv2.imshow("Image", img)
            #cv2.imshow("Frame", grayframe)
            #cv2.imshow("img3", img3)

            pixmap = self.convert_cv_to_pixmap(frame)
            self.live_image_label.setPixmap(pixmap)


            key = cv2.waitKey(1)
            if key == 27:
                break

        self._camera_device.release()
        cv2.destroyALLWindows()
        #TODO run SIFT on the captured frame

        # pixmap = self.convert_cv_to_pixmap(frame)
        # self.live_image_label.setPixmap(pixmap)

    def SLOT_toggle_camera(self):
        if self._is_cam_enabled:
            self._timer.stop()
            self._is_cam_enabled = False
            self.toggle_cam_button.setText("&Enable camera")
        else:
            self._timer.start()
            self._is_cam_enabled = True
            self.toggle_cam_button.setText("&Disable camera")

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    myApp = My_App()
    myApp.show()
    sys.exit(app.exec_())