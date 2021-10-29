import numpy as np
import serial
import datetime as dt
import os
import matplotlib.pyplot as plt
import matplotlib
import time
from multiprocessing import Process, Queue

class BlitManager:

    def __init__(self, canvas, animated_artists=()):
        """
        Parameters
        ----------
        canvas : FigureCanvasAgg
            The canvas to work with, this only works for sub-classes of the Agg
            canvas which have the `~FigureCanvasAgg.copy_from_bbox` and
            `~FigureCanvasAgg.restore_region` methods.

        animated_artists : Iterable[Artist]
            List of the artists to manage
        """
        self.canvas = canvas
        self._bg = None
        self._artists = []

        for a in animated_artists:
            self.add_artist(a)
        # grab the background on every draw
        self.cid = canvas.mpl_connect("draw_event", self.on_draw)

    def on_draw(self, event):
        """Callback to register with 'draw_event'."""
        cv = self.canvas
        if event is not None:
            if event.canvas != cv:
                raise RuntimeError
        self._bg = cv.copy_from_bbox(cv.figure.bbox)
        self._draw_animated()

    def add_artist(self, art):
        """
        Add an artist to be managed.

        Parameters
        ----------
        art : Artist

            The artist to be added.  Will be set to 'animated' (just
            to be safe).  *art* must be in the figure associated with
            the canvas this class is managing.

        """
        if art.figure != self.canvas.figure:
            raise RuntimeError
        art.set_animated(True)
        self._artists.append(art)

    def _draw_animated(self):
        """Draw all of the animated artists."""
        fig = self.canvas.figure
        for a in self._artists:
            fig.draw_artist(a)

    def update(self):
        """Update the screen with animated artists."""
        cv = self.canvas
        fig = cv.figure
        # paranoia in case we missed the draw event,
        if self._bg is None:
            self.on_draw(None)
        else:
            # restore the background
            cv.restore_region(self._bg)
            # draw all of the animated artists
            self._draw_animated()
            # update the GUI state
            cv.blit(fig.bbox)
        # let the GUI event loop process anything it has to do
        cv.flush_events()



def animated_plot_process(thermistor_queue, n_samples):
    matplotlib.use('Qt5Agg')
    
    # prep data vector
    frame_num = 0
    data = np.zeros((n_samples,))

    # make a new figure
    fig, ax = plt.subplots()
    # add a line
    (ln,) = ax.plot(np.arange(n_samples), data, animated=True)
    ax.set_xlim((0,n_samples))
    ax.set_ylim((0,1))

    # add a frame number
    fr_number = ax.annotate(
        "0",
        (0, 1),
        xycoords="axes fraction",
        xytext=(10, -10),
        textcoords="offset points",
        ha="left",
        va="top",
        animated=True,
    )
    bm = BlitManager(fig.canvas, [ln, fr_number])
    # make sure our window is on the screen and drawn
    plt.show(block=False)
    plt.pause(1)

    while True:
        data = thermistor_queue.get()
        frame_num += 1
        if len(data)==0:
            print('Breaking...')
            plt.close()
            break
        else:
            ln.set_ydata(data)
            fr_number.set_text("frame: {j}".format(j=frame_num))
            bm.update()
            

def main_from_ipynb(data_queue, n_samples):
    """Same as main, but mimic the situation where thermistor data is coming in from the ipynb itself.
    """
    
    animate_process = Process(target=animated_plot_process, args=(data_queue, n_samples))
    animate_process.start()
    return animate_process
    
            
def main():
    n_samples = 400
    data_queue = Queue()
    animate_process = Process(target=animated_plot_process, args=(data_queue, n_samples))
    animate_process.start()

    for j in range(100):
        data = np.random.random((n_samples,))
        t1 = time.time()
        data_queue.put(data)
        print(time.time() - t1)  # report time to pickle this np array
    data_queue.put(tuple())
    animate_process.join()
    print(animate_process.exitcode)
    print('finished animate process')