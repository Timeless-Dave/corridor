import React from 'react';
import {Composition} from 'remotion';
import {Film} from './Film';
import film from './film.json';

export const Root: React.FC = () => (
  <Composition id="Corridor" component={Film} durationInFrames={film.totalFrames} fps={film.fps} width={1920} height={1080} />
);
