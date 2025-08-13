import os
import sys

os.environ["QT_API"] = "pyside6"

from pathlib import Path
from typing import Dict, Tuple

import qtawesome as qta
from qtpy.QtWidgets import (
	QDialog,
	QFormLayout,
	QVBoxLayout,
	QLineEdit,
	QCheckBox,
	QDialogButtonBox,
	QComboBox,
	QWidget,
	QPushButton,
	QLabel,
	QTreeWidget,
	QTreeWidgetItem,
	QMenu,
	QHeaderView,
	QTableWidgetItem,
	QStyle,
	QWidgetAction,
	QMainWindow,
	QApplication,
	QFileDialog,
	QProgressBar,
)

from qtpy.QtUiTools import QUiLoader
from qtpy.QtCore import Qt, QTimer, QPoint, QFile, QObject,QThread, Signal, QUrl, QEvent
from qtpy.QtGui import QColor, QIcon, QMovie

from fxgui import fxwidgets, fxutils, fxdcc, fxstyle
from fxgui.fxicons import get_icon

import cv2 as cv
import time

rmantree = os.environ.get("RMANTREE")
sys.path.append(f"{rmantree}/bin")

import tractor.api.author as author

class DenoisePouetUI(QMainWindow):

	def __init__(self):
		super().__init__()


		self.denoiser = TractorDenoiser()


		self.uiPathMainUi = str(Path(r"ui\denoisePouet.ui"))
		self.iconPath = str(Path(r"images\iconDenoisePouet.png"))

		_ = QUiLoader() 
		application = fxwidgets.FXApplication()
		application.setStyle(fxstyle.FXProxyStyle())
	
		self.window = fxwidgets.FXMainWindow(
			project="denoisePouet",
			version="0.0.1",
			company="\u00A9 P.Kervaut",
			ui_file=str(self.uiPathMainUi),
			)

		self.icon = QIcon(self.iconPath)
		self.window.setWindowTitle("DenoisePouet")
		self.window.resize(800,100)

		self.window.setWindowIcon(self.icon)
		self.window.toolbar.hide()
		self.window.banner.hide()

		ui_file = QFile(self.uiPathMainUi)
		ui_file.open(QFile.ReadOnly)
		loader = QUiLoader()
		self.uiMain = loader.load(ui_file)
		ui_file.close()
		self.window.setCentralWidget(self.uiMain)


		self.filePathInput_var = self.uiMain.findChild(QLineEdit,"lineEdit_LPE")
		self.filePathInput_var.setAcceptDrops(True)
		self.filePathInput_var.installEventFilter(self)
		self.checkAnimation = self.uiMain.findChild(QCheckBox, "checkBox_Animation")
		self.title_var = self.uiMain.findChild(QLineEdit, "lineEdit_Title") 
		self.projectName_var = self.uiMain.findChild(QLineEdit, "lineEdit_Project")
		self.crossedFrame = self.uiMain.findChild(QCheckBox, "checkBox_CrossedFrame")
		self.maxActive_var =self.uiMain.findChild(QLineEdit, "lineEdit_MaxActive")

		self.switchLocal = self.uiMain.findChild(QComboBox, "comboBox_Local")
		
		self.browse = self.uiMain.findChild(QPushButton, "Button_Browse")
		self.browse.clicked.connect(self.select_folder)

		self.start = self.uiMain.findChild(QPushButton, "Button_Start")
		self.start.clicked.connect(self.start_action)
	
		self.window.show()

	
	def eventFilter(self, obj, event):
		if obj is self.filePathInput_var:
			if event.type() == QEvent.DragEnter:
				if event.mimeData().hasUrls() or event.mimeData().hasText():
					event.acceptProposedAction()
					return True
			elif event.type() == QEvent.Drop:
				if event.mimeData().hasUrls():
					urls = event.mimeData().urls()
					if urls:
						self.filePathInput_var.setText(urls[0].toLocalFile())
				elif event.mimeData().hasText():
					self.filePathInput_var.setText(event.mimeData().text())
				event.acceptProposedAction()
				return True
		return super().eventFilter(obj, event)
	
	def eventFilter(self, obj, event):
		if obj is self.filePathInput_var:
			if event.type() == QEvent.DragEnter:
				if event.mimeData().hasUrls() or event.mimeData().hasText():
					event.acceptProposedAction()
					return True
			elif event.type() == QEvent.Drop:
				if event.mimeData().hasUrls():
					urls = event.mimeData().urls()
					if urls:
						self.filePathInput_var.setText(urls[0].toLocalFile())
				elif event.mimeData().hasText():
					self.filePathInput_var.setText(event.mimeData().text())
				event.acceptProposedAction()
				return True
		return super().eventFilter(obj, event)


	def select_folder(self):

		file_path, _ = QFileDialog.getOpenFileName()

		if file_path:

			self.filePathInput_var.setText(file_path)

		
	def start_action(self):

		print(self.switchLocal.currentIndex())
		
		if self.crossedFrame.isChecked() :

			self.crossedFrame_var = "cross"
		else :
			self.crossedFrame_var = ""
		
		if self.checkAnimation.isChecked() :
			animation = True
			self.denoiser.singleOrAllImages(self.filePathInput_var.text(), animation)
		else :
			animation = 0
		
		if self.switchLocal.currentIndex() == 0 :

			print("start in tractor")
			
			self.denoiser.updateImagesList(self.filePathInput_var.text(), animation)
			directory = self.denoiser.defReturnDirectory(self.filePathInput_var.text())
			self.waitingScreen = WaitingScreen(mode = "tractor")
			
			job = self.denoiser.createRenderJob(self.title_var.text(),self.projectName_var.text(),self.maxActive_var.text(),self.crossedFrame_var,directory)
			job.spool()
	
			print("Folder Path:", self.filePathInput_var.text())
			print("Title:", self.title_var.text())
			print("Project:", self.projectName_var.text())
			print("Checkbox State:", self.crossedFrame_var)
			print("maxActive:", self.maxActive_var.text())

			msg="denoise tractor on the farm"
			lvl=fxwidgets.SUCCESS
			self.window.statusBar().showMessage(msg, lvl)

		else : 

			print("start in local")

			msg = "denoise Local"
			lvl = fxwidgets.SUCCESS
			self.window.statusBar().showMessage(msg, lvl)
		
			self.denoiser.updateImagesList(self.filePathInput_var.text(), animation)
			directory = self.denoiser.defReturnDirectory(self.filePathInput_var.text())
			
			self.waitingScreen = WaitingScreen(mode="local")
		
			# Thread + Worker setup
			self.thread = QThread()
			self.worker = LocalDenoiseWorker(self.denoiser, self.crossedFrame_var, directory)
			self.worker.moveToThread(self.thread)
		
			self.thread.started.connect(self.worker.run)
			self.worker.progress.connect(self.waitingScreen.update_progress)
			self.worker.finished.connect(self.waitingScreen.close)
			self.worker.finished.connect(self.thread.quit)
			self.worker.finished.connect(self.worker.deleteLater)
			self.thread.finished.connect(self.thread.deleteLater)
		
			self.thread.start()


class WaitingScreen():

	def __init__(self,mode):

		self.mode = mode
		print(self.mode)
	
		self.uiPathLoadingUI = str(Path(r"ui\denoisePouetLoad.ui"))
		self.iconPath  = str(Path(r"images\iconDenoisePouet.png"))
		self.movie01Path = str(Path(r"images\movie01.gif"))
		self.movie02Path = str(Path(r"images\movie02.gif"))
		self.movie03Path = str(Path(r"images\movie03.gif"))

		_ = QUiLoader() 

		self.windowLoad = fxwidgets.FXMainWindow(
			project="denoisePouet",
			version="0.0.1",
			company="\u00A9 P.Kervaut",
			ui_file=str(self.uiPathLoadingUI),
			)

		self.windowLoad.setWindowTitle("DenoisePouetLoading")
		self.windowLoad.resize(600,100)
		
		self.icon = QIcon(self.iconPath)
		self.windowLoad.setWindowIcon(self.icon)
		self.windowLoad.toolbar.hide()
		self.windowLoad.banner.hide()

		ui_file = QFile(self.uiPathLoadingUI)
		ui_file.open(QFile.ReadOnly)
		loader = QUiLoader()
		self.uiLoad = loader.load(ui_file)
		ui_file.close()
		self.windowLoad.setCentralWidget(self.uiLoad)

		self.labelMovie = self.uiLoad.findChild(QLabel, "label_Gif")
		self.labelMovie.setScaledContents(True)

		self.loadingBar = self.uiLoad.findChild(QProgressBar, "progressBar")
		self.loadingBar.setValue(0)
		
		if self.mode == "tractor" :

			self.movieWait = QMovie(self.movie01Path)
			self.labelMovie.setMovie(self.movieWait)
			self.movieWait.setSpeed(100)
			self.movieWait.jumpToFrame(0)
			self.movieWait.start()
		
			self.progress = 0
			self.timer = QTimer()
			self.timer.timeout.connect(self.waitingTractorStep)
			self.timer.start(10)

		else :

			self.movieWait = QMovie(self.movie01Path)
			self.labelMovie.setMovie(self.movieWait)
			self.movieWait.setSpeed(100)
			self.movieWait.jumpToFrame(0)
			self.movieWait.start()

		self.windowLoad.show()
		
	def waitingTractorStep(self):
		
		self.progress += 1
		self.loadingBar.setValue(self.progress)

		if self.progress == 69 :

			self.timer.stop()
			QTimer.singleShot(400, self.reStart)
			return

		if self.progress == 99 :

			self.timer.stop()
			QTimer.singleShot(800, self.reStart)
			return

		if self.progress >= 100 :

			self.timer.stop()
			QTimer.singleShot(1000, self.end)

	def update_progress(self, count, total, frame):

		msg=f"{frame} done"
		lvl=fxwidgets.INFO
		self.windowLoad.statusBar().showMessage(msg, lvl)

		percent = int((count / total) * 100)
		self.loadingBar.setValue(percent)
		print(f"Progress {count}/{total} — Frame: {frame}")
			
	def reStart(self):
		self.timer.start(30)

	def end(self):

		self.movie02 = QMovie(self.movie02Path)
		self.labelMovie.setMovie(self.movie02)
		self.movie02.setSpeed(100)
		self.movie02.jumpToFrame(0)
		self.movie02.start()

		print("Chargement terminé")

		QTimer.singleShot(6000, self.close)
	

	def close(self):

		self.windowLoad.close()

class TractorDenoiser:

	def __init__(self, parent=None):
		"""Initialize the class"""
		self.render_list = []


	def defReturnDirectory(self, imagePath):

		filePathInput = imagePath
		directory = os.path.dirname(imagePath) + "/"
		filename = os.path.basename(imagePath)
		return directory

	def singleOrAllImages(self, imagePath, animation):

		import re
		filePathInput = imagePath
		directory = os.path.dirname(imagePath) + "/"
		filename = os.path.basename(imagePath)
		imagePathAnim = re.sub(r"\.(\d+)\.", r".####.", filename)
		return imagePathAnim

	def updateImagesList(self, imagePath, animation):

		import re
		filePathInput = imagePath
		directory = os.path.dirname(imagePath) + "/"
		filename = os.path.basename(imagePath)

		if animation == True :
			imagePathAnim = self.singleOrAllImages(imagePath, animation)
			filename = imagePathAnim


		if os.path.isfile(filePathInput) and animation != True:

			self.render_list.append(filePathInput)
			print(self.render_list)
		else:
			print(filename)
			if "#" in filename:

				longest_seq = max(re.findall("[#]+", filename), key=len)

				prefix, suffix = filename.split(longest_seq)

				numbers = len(longest_seq)

				file_list = os.listdir(directory)

				re_nb = r"[0-9]{" + str(numbers) + "}"

				for f in file_list:
					
					if re.fullmatch(prefix + re_nb + suffix, f):
						if f.endswith(".exr"):
							f= os.path.join(directory, f)
							self.render_list.append(f)


		render_count = len(self.render_list)
		print('blabla', self.render_list)
		return self.render_list


	def templateJob(self, title, service, projet, maxactive):

		"""Create Tractor Job with its attributes"""
		job = author.Job()
		job.title = f"{title}"
		job.projects = [projet]
		job.priority = 100
		job.maxactive = maxactive
		job.service = "denoise"
		job.serialsubtasks = True
		return job 

	def createRenderJob(self, title, projet, maxactive, cross, directory):

		job = self.templateJob(f"> DENOISE < {title}", "denoise",projet ,maxactive)
		tractor_task = author.Task()
		tractor_task.title = f"denoisePouet"
		for frame in self.render_list:
			tractor_task.addChild(self.createTractorTask(title,frame,cross,projet,directory))
		job.addChild(tractor_task)
		self.render_list.clear()
		return job 

	def createTractorTask(self, title, frame, cross, projet, directory):
		"""Create Tractor Task with the associated command to execute the export (see scripts folder)"""
		title = f"> DENOISE < {title}"
		tractor_task = author.Task()
		tractor_task.title = f"{title}"
		tractor_task.service = "denoise_batch"
		tractor_task_cmd = author.Command()
		tractor_task_cmd.tags = ["Denoise"]
		"""path de la sortie ( done un dossier denoise à coté des images déja calculer)"""
		tractor_task_cmd.argv = ["denoise_batch"]

		tractor_task_cmd.argv.append("-o")
		tractor_task_cmd.argv.append(f"{directory}denoised")

		tractor_task_cmd.argv.append("--crossframe")
		tractor_task_cmd.argv.append(cross)

		tractor_task_cmd.argv.append(f"{frame}")
		tractor_task.addCommand(tractor_task_cmd)
		return tractor_task

	def localDenoise(self, cross, directory):

		count = 0
	
		for frame in self.render_list :

			os.system(f"denoise_batch -o {directory}denoised -cf {cross} {frame}")
			count +=1
			yield frame
		
class LocalDenoiseWorker(QObject):

	progress = Signal(int, int, str)  # count, total, frame
	finished = Signal()

	def __init__(self, denoiser, cross, directory):

		super().__init__()

		self.denoiser = denoiser
		self.cross = cross
		self.directory = directory

	def run(self):

		total = len(self.denoiser.render_list)

		for count, frame in enumerate(self.denoiser.render_list, start=1):

			os.system(f"denoise_batch -o {self.directory}denoised -cf {self.cross} {frame}")
			self.progress.emit(count, total, frame)
		
		self.finished.emit()

if __name__ == "__main__":
	app = fxwidgets.FXApplication()
	app.setStyle(fxstyle.FXProxyStyle())

	window = DenoisePouetUI()
	sys.exit(app.exec_())
